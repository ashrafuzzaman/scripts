export function parseArgument(pattern) {
  const args = process.argv[2];
  const match = args.match(pattern);
  if(!match) {
    console.warn(`Missing argument, ${pattern}`);
  }
  return match.groups;
};
