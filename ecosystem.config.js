module.exports = {
  apps: [{
    name: 'showeasy-chatbot',
    script: 'src/main.py',
    interpreter: '.venv/bin/python',
    cwd: '~/chatbot_showeasy',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true,
    merge_logs: true
  }]
};