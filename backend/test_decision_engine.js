#!/usr/bin/env node
// Test script to simulate server calling decision_engine.py

const { spawn } = require('child_process');
const path = require('path');

const inputData = {
    plot_id: 'test1',
    farmer_id: 'farmer1',
    features_data: {
        disease_detection: { risk_level: 'low', probability: 0.2 },
        water_stress: { stress: 'moderate', score: 50 },
        pest_risk: { risk_level: 'low', confidence: 0.8 },
        stage_classifier: { stage: 'vegetative' }
    },
    current_crop: 'wheat'
};

const pythonScriptPath = path.join(__dirname, 'decision_engine.py');

console.log('=== Testing decision_engine.py ===\n');
console.log('Input data:', JSON.stringify(inputData, null, 2));
console.log(`\nCalling: python ${pythonScriptPath}...\n`);

const pythonProcess = spawn('python', [pythonScriptPath, JSON.stringify(inputData)]);

let outputData = '';
let errorOutput = '';

pythonProcess.stdout.on('data', (data) => {
    outputData += data.toString();
});

pythonProcess.stderr.on('data', (data) => {
    errorOutput += data.toString();
});

pythonProcess.on('close', (code) => {
    console.log(`\n=== Python Exit Code: ${code} ===\n`);
    
    if (errorOutput) {
        console.log('STDERR:', errorOutput);
    }
    
    console.log('STDOUT:', outputData);
    
    if (code === 0) {
        try {
            const result = JSON.parse(outputData.trim());
            console.log('\n=== Parsed Result ===');
            console.log(JSON.stringify(result, null, 2));
        } catch (e) {
            console.error('Parse error:', e.message);
        }
    }
});
