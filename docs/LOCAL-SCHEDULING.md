# Local scheduled collection (optional)

GitHub Actions is the **primary** persistence mechanism — the five
workflows (discovery, collection, recheck, verification via the weekly
audit, gap retry folded into collection) run without any machine being
on. Use local scheduling only as a supplement on a machine you
control, with an ordinary, transparent OS scheduler. Never stealth
persistence; every entry below is visible, documented, and removable.

The interactive session that authored this repository runs in an
ephemeral cloud container (no scheduler survives it), so nothing was
installed locally — these are the exact configurations to apply on a
suitable machine.

## Scripts (repository-controlled)

| Script | Purpose |
|--------|---------|
| `scripts/discover.sh` | Sitemap + Federal Register enumeration |
| `scripts/collect-pending.sh` | Consume up to `$LIMIT` pending queue URLs |
| `scripts/verify-archive.sh` | Re-hash local objects against content addresses |

Local runs store objects in `./archive` (git-ignored). Local objects
are FETCHED/VERIFIED but not DURABLY_ARCHIVED until copied to durable
storage (a release, or an off-machine backup).

## Linux — systemd timer (preferred)

`~/.config/systemd/user/fincen-boi-collect.service`:

```ini
[Unit]
Description=FinCEN-BOI pending-queue collection

[Service]
Type=oneshot
WorkingDirectory=%h/FinCEN-BOI
ExecStart=%h/FinCEN-BOI/scripts/collect-pending.sh
```

`~/.config/systemd/user/fincen-boi-collect.timer`:

```ini
[Unit]
Description=Daily FinCEN-BOI collection

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

Enable: `systemctl --user daemon-reload && systemctl --user enable --now fincen-boi-collect.timer`

## Linux — cron (acceptable)

```cron
17 3 * * * cd $HOME/FinCEN-BOI && ./scripts/discover.sh >> logs/discover.log 2>&1
47 4 * * * cd $HOME/FinCEN-BOI && ./scripts/collect-pending.sh >> logs/collect.log 2>&1
11 6 * * 0 cd $HOME/FinCEN-BOI && ./scripts/verify-archive.sh >> logs/verify.log 2>&1
```

## macOS — launchd

`~/Library/LaunchAgents/org.fincen-boi.collect.plist` with a
`ProgramArguments` entry pointing at `scripts/collect-pending.sh` and a
`StartCalendarInterval` of your choosing; load with
`launchctl load ~/Library/LaunchAgents/org.fincen-boi.collect.plist`.

## Windows — Task Scheduler

Create a basic task running
`sh.exe scripts/collect-pending.sh` (via Git Bash/WSL) on a daily
trigger.

If elevated permissions would be required and are unavailable, do not
bypass them — GitHub Actions already provides the active persistence.
