import { useState, type FormEvent } from "react";
import { LoginLensBackdrop } from "./LoginLensBackdrop";
import { FIXTURE_USER } from "./fixtureUser";
import styles from "./Login.module.css";

/**
 * The threshold (§8). One calm card on quiet Paper, cooled to Riso-Blue-dominant;
 * the dimmed hero lens sits behind it. The ONE screen allowed to be plain — a govt
 * login should look sober. Success is MOCKED (fixture user); no network call ever.
 */
export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState<string>(FIXTURE_USER.username);
  const [passphrase, setPassphrase] = useState<string>(FIXTURE_USER.passphrase);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    // Local flip only — the demo accepts the fixture user. Nothing leaves this machine.
    onSuccess();
  };

  return (
    <div className={styles.threshold}>
      <LoginLensBackdrop />
      {/* the cooldown wash — the colour shifts Riso-Blue as you enter the serious part */}
      <div className={styles.wash} aria-hidden="true" />

      <main className={styles.card}>
        <div className={styles.brand}>
          <span className={styles.wordmark}>DRISHTI</span>
          <span className={styles.tagline}>See through the noise.</span>
        </div>

        <h1 className={styles.heading}>Sign in to the workstation</h1>

        <form className={styles.form} onSubmit={submit}>
          <label className={styles.field}>
            <span className={styles.label}>Officer ID</span>
            <input
              className={styles.input}
              type="text"
              value={username}
              autoComplete="off"
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label className={styles.field}>
            <span className={styles.label}>Passphrase</span>
            <input
              className={styles.input}
              type="password"
              value={passphrase}
              autoComplete="off"
              onChange={(e) => setPassphrase(e.target.value)}
            />
          </label>
          <button className={styles.submit} type="submit">
            Enter the workstation
          </button>
        </form>

        <p className={styles.note}>Runs fully offline. Case data never leaves this machine.</p>

        <div className={styles.security}>
          <span className={styles.badge}>
            <span className={styles.dot} /> OFFLINE
          </span>
          <span className={styles.mono}>private workstation</span>
          <span className={styles.mono}>no external calls</span>
        </div>
      </main>

      {/* the diya rests at the corner, dim — "I'll be on the other side." */}
      <div className={styles.diya} aria-hidden="true" title="On the other side.">
        <span className={styles.diyaFlame} />
      </div>
    </div>
  );
}
