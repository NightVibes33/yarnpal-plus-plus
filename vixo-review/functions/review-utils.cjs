// A process-scoped UUID is not an iOS hardware identifier.
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
function isValidLaunchId(value) {
  return typeof value === "string" && value.length === 36 && uuidPattern.test(value);
}
module.exports = { isValidLaunchId };
