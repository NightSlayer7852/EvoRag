const colors = {
  reset: '\x1b[0m',
  gray: '\x1b[90m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  magenta: '\x1b[35m',
};

function ts() {
  return colors.gray + new Date().toISOString() + colors.reset;
}

const logger = {
  info:  (...args) => console.log(  ts(), colors.blue   + '[INFO] ' + colors.reset, ...args),
  warn:  (...args) => console.warn( ts(), colors.yellow  + '[WARN] ' + colors.reset, ...args),
  error: (...args) => console.error(ts(), colors.red     + '[ERROR]' + colors.reset, ...args),
  debug: (...args) => console.log(  ts(), colors.magenta + '[DEBUG]' + colors.reset, ...args),
  success:(...args)=> console.log(  ts(), colors.green   + '[OK]   ' + colors.reset, ...args),
  http:  (method, url, status, ms) => {
    const statusColor = status >= 500 ? colors.red : status >= 400 ? colors.yellow : colors.green;
    console.log(ts(), colors.cyan + '[HTTP] ' + colors.reset,
      colors.cyan + method.padEnd(6) + colors.reset, url,
      statusColor + status + colors.reset,
      colors.gray + `(${ms}ms)` + colors.reset
    );
  }
};

module.exports = logger;
