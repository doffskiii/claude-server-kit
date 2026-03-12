module.exports = {
  apps: [{
    name: 'brain-monitor',
    script: 'scripts/monitor.py',
    interpreter: '/root/.local/bin/uv',
    interpreter_args: 'run --directory /root/brain python',
    cwd: '/root/brain',
    restart_delay: 10000,
    max_restarts: 10,
    autorestart: true,
  }, {
    name: 'brain-whisper',
    script: 'src/brain/whisper_server.py',
    interpreter: '/root/.local/bin/uv',
    interpreter_args: 'run --directory /root/brain python',
    cwd: '/root/brain',
    restart_delay: 5000,
    max_restarts: 5,
    autorestart: true,
  }]
};
