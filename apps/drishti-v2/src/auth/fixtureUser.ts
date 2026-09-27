// The mocked demo user (§8). Auth is the backend's job; the frontend only needs
// the screen + a success path. NEVER phones home — success is a local state flip.
export const FIXTURE_USER = {
  username: "officer.ntro",
  name: "Investigating Officer",
  role: "NTRO · Cyber Forensics",
  // The demo passphrase is prefilled and accepted locally. No network, no hashing,
  // no validation call — this is a fixture, not real credential handling.
  passphrase: "sih26146",
} as const;
