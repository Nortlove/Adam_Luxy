/**
 * v1 single-user auth stub.
 *
 * Phase A uses a single hard-coded user identified by an env-configured
 * email + Bearer token. When Phase C multi-tenancy lands this module is
 * replaced with a proper SSO flow (Clerk or Auth.js) and per-session
 * user resolution — nothing outside this file should depend on the auth
 * shape directly.
 */

export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  role: "superadmin";
};

export function getCurrentUser(): CurrentUser {
  const email = process.env.INFORMATIV_USER_EMAIL ?? "chris@informativgroup.com";
  const name = process.env.INFORMATIV_USER_NAME ?? "Chris Nocera";
  return {
    id: "user:chris",
    email,
    name,
    role: "superadmin",
  };
}

export function getApiToken(): string | undefined {
  return process.env.INFORMATIV_API_TOKEN;
}
