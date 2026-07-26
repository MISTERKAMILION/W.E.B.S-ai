#!/usr/bin/env node
/**
 * Node.js bridge for Puter.js Gemini API
 * Called from Python to access free Gemini models
 */

const path = require('path');

const puterPath = path.join(__dirname, 'node_modules', '@heyputer', 'puter.js');
let puter;
try {
    puter = require(puterPath).puter;
} catch (e) {
    console.log(JSON.stringify({ success: false, error: 'Missing dependency: run npm install in ' + __dirname }));
    process.exit(1);
}

async function generate(prompt, options = {}) {
    const model = options.model || 'gemini-2.0-flash';
    const response = await puter.ai.chat(prompt, {
        model,
        stream: false,
        temperature: options.temperature || 0.7,
        max_tokens: options.max_tokens || 1024,
    });
    return { success: true, content: response, model };
}

async function chat(messages, options = {}) {
    const model = options.model || 'gemini-2.0-flash';
    const response = await puter.ai.chat(messages, {
        model,
        stream: false,
        temperature: options.temperature || 0.7,
        max_tokens: options.max_tokens || 1024,
    });
    return { success: true, content: response, model };
}

async function main() {
    const args = process.argv.slice(2);
    const command = args[0];
    const input = args[1] ? JSON.parse(args[1]) : null;
    const options = args[2] ? JSON.parse(args[2]) : {};

    let result;
    try {
        switch (command) {
            case 'generate':
                result = await generate(input, options);
                break;
            case 'chat':
                result = await chat(input, options);
                break;
            default:
                result = { success: false, error: `Unknown command: ${command}` };
        }
    } catch (error) {
        result = { success: false, error: error.message };
    }

    console.log(JSON.stringify(result));
}

if (require.main === module) {
    main();
}

module.exports = { generate, chat };
