import { simulateConsequences } from './harm_detection';

// Cloudflare D1 Database type declaration
declare global {
  interface D1Database {
    prepare(query: string): D1PreparedStatement;
  }
  
  interface D1PreparedStatement {
    bind(...values: any[]): D1PreparedStatement;
    first(): Promise<any>;
    all(): Promise<{ results: any[] }>;
    run(): Promise<any>;
  }
}

interface Env {
  DB: D1Database;
}

function safeJsonParse<T>(jsonString: string | null | undefined, defaultValue: T): T {
  if (!jsonString) return defaultValue;
  try {
    return JSON.parse(jsonString);
  } catch {
    return defaultValue;
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    // CORS headers for local development
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };
    
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    try {
      // Get random scenario
      if (url.pathname === '/api/get-scenario') {
        const { difficulty } = Object.fromEntries(url.searchParams);
        const difficultyNum = difficulty ? parseInt(difficulty) : 2;
        const maxDifficulty = isNaN(difficultyNum) ? 2 : difficultyNum;
        
        const scenario = await env.DB
          .prepare(`
            SELECT * FROM scenarios 
            WHERE difficulty_level <= ?
            ORDER BY RANDOM() 
            LIMIT 1
          `)
          .bind(maxDifficulty)
          .first();
        
        if (!scenario) {
          return Response.json({ error: 'No scenarios found' }, { status: 404 });
        }
        
        return Response.json({
          ...scenario,
          person_state: safeJsonParse(scenario.person_state as string, {}),
          facts: safeJsonParse(scenario.facts as string, []),
          critical_info: safeJsonParse(scenario.critical_info as string, [])
        }, { headers: corsHeaders });
      }
      
      // Simulate outcome
      if (url.pathname === '/api/simulate-outcome' && request.method === 'POST') {
        const requestBody = await request.json();
        
        if (!requestBody || typeof requestBody !== 'object') {
          return Response.json({ error: 'Invalid request body' }, { status: 400 });
        }
        
        const { scenario_id, response: aiResponse } = requestBody;
        
        if (!scenario_id || !aiResponse) {
          return Response.json({ error: 'Missing scenario_id or response' }, { status: 400 });
        }
        
        // Get scenario
        const scenario = await env.DB
          .prepare('SELECT * FROM scenarios WHERE id = ?')
          .bind(scenario_id)
          .first();
        
        if (!scenario) {
          return Response.json({ error: 'Scenario not found' }, { status: 404 });
        }
        
        // Parse JSON fields
        const scenarioData = {
          ...scenario,
          person_state: safeJsonParse(scenario.person_state as string, {}),
          facts: safeJsonParse(scenario.facts as string, []),
          critical_info: safeJsonParse(scenario.critical_info as string, [])
        };
        
        // Calculate harm
        const outcome = simulateConsequences(aiResponse, scenarioData);
        
        // Store experience
        await env.DB
          .prepare(`
            INSERT INTO experiences 
            (scenario_id, ai_response, actual_harm, harm_breakdown, learned_lesson, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
          `)
          .bind(
            scenario_id,
            aiResponse,
            outcome.total_harm,
            JSON.stringify(outcome.breakdown),
            outcome.lesson,
            new Date().toISOString()
          )
          .run();
        
        return Response.json(outcome, { headers: corsHeaders });
      }
      
      // Get training statistics
      if (url.pathname === '/api/stats') {
        const stats = await env.DB
          .prepare(`
            SELECT 
              COUNT(*) as total_episodes,
              AVG(actual_harm) as avg_harm,
              MIN(actual_harm) as best_harm,
              MAX(actual_harm) as worst_harm
            FROM experiences
            WHERE timestamp > datetime('now', '-24 hours')
          `)
          .first();
        
        const recentTrend = await env.DB
          .prepare(`
            SELECT 
              CAST(strftime('%H', timestamp) AS INTEGER) as hour,
              AVG(actual_harm) as avg_harm
            FROM experiences
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY hour
            ORDER BY hour
          `)
          .all();
        
        return Response.json({
          stats,
          trend: recentTrend.results
        }, { headers: corsHeaders });
      }
      
      return new Response('Not found', { status: 404, headers: corsHeaders });
      
    } catch (error) {
      return Response.json({
        error: error instanceof Error ? error.message : 'Unknown error'
      }, { 
        status: 500,
        headers: corsHeaders
      });
    }
  }
};
