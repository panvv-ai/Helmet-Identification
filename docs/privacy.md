# Privacy

Helmet Workbench processes biometric and workplace imagery. Use it only with appropriate authorization and legal basis.

## Data Stored Locally

- Employee number and name.
- Face sample crops.
- Identity model files and metadata.
- Camera evidence images retained for formal records.
- Photo/video analysis outputs.
- Attendance and violation metadata.
- Persistent job history.

All runtime content is stored below `storage/` and excluded from Git.

## Network Behavior

- The web server listens on `127.0.0.1` by default.
- Face samples, inference inputs and business records are not sent to external services.
- The only optional external request is downloading the versioned model artifact from GitHub Releases.

## Retention

- Evidence retention is configurable.
- Deleting an employee removes active samples and deactivates the profile.
- Historical attendance and violation records retain the employee number and name snapshot for audit continuity.
- Operators should define their own retention period and remove obsolete evidence and database copies.

## Limitations

The application has no account system, transport encryption, liveness detection or multi-tenant isolation. Do not expose it directly to a public network without adding authentication, TLS, network controls and a formal privacy/security review.

## Recommendations

1. Inform workers and obtain consent before enrollment.
2. Limit access to the local machine and `storage/` directory.
3. Keep a documented evidence-retention period.
4. Verify local laws for biometric data and employee monitoring.
5. Do not use low-confidence automated decisions as the sole basis for disciplinary action.
