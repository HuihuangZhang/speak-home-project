You have 50 minutes to implement the following two features. You may use any tools, references, or AI assistance you'd like — we're interested in the quality of what you ship, not how you got there.
Feature A — Lock down the test utilities endpoint
The /test-utils/sessions/{id}/force-expire endpoint is currently always mounted with no authentication and no ownership check. Fix it:
Gate the router behind an environment variable (ENABLE_TEST_UTILS=true), so it only mounts when that variable is set
Add an auth dependency so only authenticated users can call it
Add an ownership check so a user can only force-expire their own sessions
The existing Playwright E2E tests depend on this endpoint — they should still pass after your changes.

Feature B — Session duration tracking
Sessions have a created_at timestamp but no duration. Add it:
Write an Alembic migration adding a duration_seconds integer column to the sessions table
Populate it when a session transitions to COMPLETED, computing elapsed time from created_at (excluding any time spent in the PAUSED state — paused time should not count toward duration)
Surface the duration on both the dashboard session list and the session summary page
You don't need to write tests, but your code should handle edge cases you'd consider in production. We'll talk through your decisions when time is up.