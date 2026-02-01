import { Ollama } from 'ollama';



class BuddhistTrainer {
  constructor(workerUrl = 'https://buddhist-ai-worker.mistykmedia.workers.dev') {
    this.ollama = new Ollama({ host: 'http://localhost:11434' });
    this.workerUrl = workerUrl;
    this.modelName = 'tinyllama:1.1b';
    this.systemPrompt = this.buildSystemPrompt();
  }

  buildSystemPrompt() {
    return `You are an AI assistant learning to practice Right Speech from Buddhist ethics. 

Your goal is to respond helpfully while minimizing harm through:
- Truthfulness without deception
- Kindness without harshness  
- Completeness without harmful omission
- Genuine help without manipulation

Consider the person's emotional state and vulnerability. Speak with wisdom and compassion.`;
  }

  async getRandomScenario(maxDifficulty = 5) {
    try {
      const response = await fetch(`${this.workerUrl}/api/get-scenario?difficulty=${maxDifficulty}`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('Error fetching scenario:', error);
      return null;
    }
  }

  async generateResponse(scenario) {
    const prompt = `Context: ${scenario.context}

Person's state: ${JSON.stringify(scenario.person_state)}
Known facts: ${JSON.stringify(scenario.facts)}
Critical information: ${JSON.stringify(scenario.critical_info)}

Please respond with Right Speech - truthful, kind, complete, and genuinely helpful:`;

    try {
      const response = await this.ollama.generate({
        model: this.modelName,
        prompt: prompt,
        system: this.systemPrompt,
        options: {
          temperature: 0.7,
          top_p: 0.9
        }
      });
      
      return response.response.trim();
    } catch (error) {
      console.error('Error generating response:', error);
      return null;
    }
  }

  async recordExperience(scenarioId, response, harm) {
    try {
      const outcome = await fetch(`${this.workerUrl}/api/simulate-outcome`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_id: scenarioId,
          response: response
        })
      });
      
      if (outcome.ok) {
        const result = await outcome.json();
        return result;
      }
    } catch (error) {
      console.error('Error recording experience:', error);
    }
    return null;
  }

  async updateSystemPrompt(avgHarm) {
    // Reset to base prompt and add feedback
    this.systemPrompt = this.buildSystemPrompt();
    
    if (avgHarm > 0.6) {
      this.systemPrompt += `\n\nRecent feedback: You've been causing harm. Focus more on:
- Checking facts carefully before responding
- Using gentler language, especially with vulnerable people
- Including important warnings and context`;
    } else if (avgHarm < 0.2) {
      this.systemPrompt += `\n\nRecent feedback: Good progress! Continue applying Right Speech principles while being helpful.`;
    }
  }

  async trainEpisode() {
    console.log('Starting training episode...');
    
    // Get scenario
    const scenario = await this.getRandomScenario();
    if (!scenario) {
      console.log('No scenarios available');
      return;
    }

    console.log(`\nScenario ${scenario.id}: ${scenario.context}`);
    console.log(`Difficulty: ${scenario.difficulty_level}, Expected harm type: ${scenario.harm_type}`);

    // Generate response
    const response = await this.generateResponse(scenario);
    if (!response) {
      console.log('Failed to generate response');
      return;
    }

    console.log(`\nAI Response: ${response}`);

    // Record experience and get harm assessment
    const outcome = await this.recordExperience(scenario.id, response, 0);
    if (!outcome) {
      console.log('Failed to record experience');
      return;
    }

    console.log(`\nHarm Score: ${outcome.total_harm.toFixed(3)}`);
    console.log(`Breakdown: D:${outcome.breakdown.deception.toFixed(2)} H:${outcome.breakdown.harshness.toFixed(2)} O:${outcome.breakdown.omission.toFixed(2)} M:${outcome.breakdown.manipulation.toFixed(2)}`);
    console.log(`Lesson: ${outcome.lesson}`);

    return { scenario, response, harm: outcome.total_harm, outcome };
  }

  async runTraining(episodes = 10) {
    console.log(`Starting Buddhist AI Training - ${episodes} episodes`);
    console.log(`Model: ${this.modelName}\n`);

    for (let i = 1; i <= episodes; i++) {
      console.log(`\n=== Episode ${i}/${episodes} ===`);
      
      try {
        await this.trainEpisode();
        
        // Brief pause between episodes
        await new Promise(resolve => setTimeout(resolve, 1000));
        
      } catch (error) {
        console.error(`Error in episode ${i}:`, error);
      }
    }

    // Show final stats
    try {
      const statsResponse = await fetch(`${this.workerUrl}/api/stats`);
      if (statsResponse.ok) {
        const { stats } = await statsResponse.json();
        console.log('\n=== Training Complete ===');
        console.log(`Episodes: ${stats.total_episodes || 0}`);
        console.log(`Average Harm: ${stats.avg_harm?.toFixed(3) || 'N/A'}`);
        console.log(`Best Performance: ${stats.best_harm?.toFixed(3) || 'N/A'}`);
        console.log(`Worst Performance: ${stats.worst_harm?.toFixed(3) || 'N/A'}`);
      }
    } catch (error) {
      console.log('\n=== Training Complete ===');
      console.log('Could not fetch final stats');
    }
  }
}

// Run training if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const trainer = new BuddhistTrainer();
  
  const episodes = parseInt(process.argv[2]) || 10;
  trainer.runTraining(episodes).catch(console.error);
}

export { BuddhistTrainer };