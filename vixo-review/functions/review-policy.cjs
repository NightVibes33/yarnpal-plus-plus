"use strict";
const { isValidLaunchId } = require("./review-utils.cjs");

/**
 * Review premium is an allowlisted, short-lived SERVER entitlement.
 * Return false for unknown users or missing/expired/disabled grants.
 */
function validApproval(user, grant, now = Date.now()) {
  if (!user || user.disabled || !grant) return false;
  const c = user.customClaims || {};
  const expiry = grant.expiresAt;
  const end = expiry && typeof expiry.toMillis === "function"
    ? expiry.toMillis()
    : expiry instanceof Date ? expiry.getTime() : NaN;
  return c.vixo_app_review === true &&
    c.vixo_demo_premium === true &&
    grant.active === true &&
    grant.premium === true &&
    Number.isFinite(end) && end > now;
}

/** Supply authenticated UID; never accept a caller-provided UID. */
async function approvedUid(uid, { getUser, getGrant, now = Date.now }) {
  if (typeof uid !== "string" || !uid) return false;
  const [user, grant] = await Promise.all([getUser(uid), getGrant(uid)]);
  return validApproval(user, grant, now());
}

/**
 * Treat every new process launch as a new VIRTUAL review-device, not a new
 * physical device. Only applies after an approved server grant.
 * Calling twice in the same process is idempotent for the same UUID.
 */
async function registerVirtualDevice(uid, launchId, services) {
  if (!isValidLaunchId(launchId)) {
    const e = new Error("launchId must be a UUID");
    e.code = "invalid-argument";
    throw e;
  }
  if (!await approvedUid(uid, services)) {
    return { review: false, registered: false };
  }
  await services.putLaunch(uid, launchId);
  return {
    review: true,
    registered: true,
    launchId,
    virtualDeviceId: launchId,
    virtualDeviceType: "app_review_process",
  };
}

module.exports = { validApproval, approvedUid, registerVirtualDevice };
