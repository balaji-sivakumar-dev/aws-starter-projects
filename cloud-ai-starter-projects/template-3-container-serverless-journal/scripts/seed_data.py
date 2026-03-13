"""
Seed script — loads 20 realistic journal entries into DynamoDB.

Works with both local DynamoDB and real AWS DynamoDB.

Usage
-----
# Local (docker compose running):
python scripts/seed_data.py

# Local with custom endpoint:
DYNAMODB_ENDPOINT=http://localhost:8000 python scripts/seed_data.py

# AWS (uses your default AWS profile / env credentials):
DYNAMODB_ENDPOINT="" AWS_DEFAULT_REGION=us-east-1 python scripts/seed_data.py

# Custom user or table:
USER_ID=alice JOURNAL_TABLE_NAME=journal-prod python scripts/seed_data.py

Environment variables
---------------------
DYNAMODB_ENDPOINT   DynamoDB endpoint URL. Defaults to http://localhost:8000 for local.
                    Set to "" or unset to use real AWS.
JOURNAL_TABLE_NAME  Table name (default: journal)
USER_ID             Owner of all seeded entries (default: dev-user)
AWS_DEFAULT_REGION  AWS region (default: us-east-1)
"""

import os
import sys
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# ── Config ────────────────────────────────────────────────────────────────────

ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:8000")
TABLE_NAME = os.getenv("JOURNAL_TABLE_NAME", "journal")
USER_ID = os.getenv("USER_ID", "dev-user")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# ── Seed data — 20 entries spanning ~5 months ─────────────────────────────────
#
# Covers three themes: work, family, travel.
# Dates span Oct 2025 – Mar 2026 across multiple ISO weeks / months.

ENTRIES = [
    # ── October 2025 ──────────────────────────────────────────────────────────
    {
        "ts": "2025-10-06T08:30:00Z",  # Week 41 — Mon
        "title": "Sprint planning for Q4 features",
        "body": (
            "Kicked off the new two-week sprint this morning. We mapped out the three "
            "big ticket items: the notification service refactor, the new dashboard "
            "widgets, and the API rate-limiting layer. I volunteered to lead the "
            "notification piece — it's overdue but finally greenlit. The team energy "
            "feels good. We finished planning by 11 am and I spent the rest of the "
            "day writing the design doc so everyone has context before we dive in tomorrow."
        ),
    },
    {
        "ts": "2025-10-12T15:00:00Z",  # Week 41 — Sun
        "title": "Family Sunday hike at Blue Ridge",
        "body": (
            "Convinced the whole family to try the 5-mile loop at Blue Ridge State Park. "
            "The kids complained for the first mile but then found a stream and forgot "
            "all about complaining. My daughter spotted a red-tailed hawk circling above "
            "the ridge — she's been into birds lately so that made her day. We packed "
            "sandwiches and ate at the summit overlook. Weather was perfect, mid-60s "
            "and crisp. Exactly the reset I needed before another busy week."
        ),
    },
    {
        "ts": "2025-10-16T19:45:00Z",  # Week 42 — Thu
        "title": "Resolved the prod memory leak — finally",
        "body": (
            "Three weeks chasing a memory leak in the analytics pipeline and tonight "
            "we finally nailed it. The culprit was a stale event listener accumulating "
            "inside a React component that was being unmounted and remounted too "
            "aggressively. Simple fix once found, but the debugging journey was brutal — "
            "heap dumps, flamegraphs, adding telemetry. Pushed the patch at 7 pm, "
            "deployed by 8. Monitoring looks clean. Wrote up the post-mortem while "
            "it was fresh. Team deserves a proper shout-out tomorrow."
        ),
    },
    {
        "ts": "2025-10-22T12:00:00Z",  # Week 43 — Wed
        "title": "My son's first soccer match",
        "body": (
            "Took the afternoon off to watch Liam's first competitive soccer match. "
            "He's been training for six weeks and was so nervous at breakfast he barely "
            "ate. His team lost 3-1 but he scored their only goal — a right-footed shot "
            "from just inside the box. The look on his face when the net moved is "
            "something I'll carry for a long time. We celebrated with ice cream after "
            "and he replayed the goal about forty times on the drive home. Best "
            "afternoon I've had in months."
        ),
    },
    {
        "ts": "2025-10-29T09:15:00Z",  # Week 44 — Wed
        "title": "Architecture review: migrating to event-driven",
        "body": (
            "Presented the event-driven migration proposal to the principal engineers "
            "today. The core idea is replacing direct service-to-service HTTP calls "
            "with an event bus so we can decouple deployments and add consumers without "
            "touching upstream services. Got a lot of good pushback on ordering "
            "guarantees and idempotency — I'll need to revise the doc with concrete "
            "examples. Overall the reception was positive. Next step is a proof-of-concept "
            "with two services before we commit to full rollout."
        ),
    },
    # ── November 2025 ─────────────────────────────────────────────────────────
    {
        "ts": "2025-11-03T07:00:00Z",  # Week 45 — Mon
        "title": "NYC business trip — Day 1",
        "body": (
            "Early flight to JFK, managed to land by 10 am. Took the AirTrain and "
            "subway into Midtown — remembered why I love cities that have working transit. "
            "Client meetings ran back-to-back from noon to 6 pm. The main topic was "
            "their data pipeline bottleneck; we walked through three proposed solutions "
            "on a whiteboard and they liked the incremental approach. Dinner with the "
            "client team at a small Italian place in Hell's Kitchen. Good food, better "
            "conversation. Checked into the hotel exhausted but feeling optimistic."
        ),
    },
    {
        "ts": "2025-11-10T18:30:00Z",  # Week 46 — Mon
        "title": "Parent-teacher conference",
        "body": (
            "Met with Emma's fourth-grade teacher after school today. The feedback was "
            "largely positive — Emma is reading two grade levels ahead and participates "
            "actively in class. The one area to watch is math; she rushes through "
            "problems and makes careless errors. Her teacher suggested timed practice "
            "games at home. We also talked about a class project on local ecosystems — "
            "Emma apparently wants to focus on migratory birds. No surprises there "
            "after the hawk sighting last month. Left feeling good, grabbed takeout "
            "on the way home."
        ),
    },
    {
        "ts": "2025-11-18T20:00:00Z",  # Week 47 — Tue
        "title": "Annual performance review prep",
        "body": (
            "Spent the evening pulling together my self-review. Looking back at the "
            "year: shipped the data ingestion rewrite on time, led three onboarding "
            "cycles for new engineers, and drove the observability initiative that cut "
            "mean-time-to-detect from 40 minutes to 8. Areas to grow: I want to speak "
            "at an external conference next year and get better at delegating sooner "
            "instead of staying heads-down too long. Writing this stuff out always "
            "feels awkward but it's useful to see the year as a coherent story rather "
            "than a blur of tickets."
        ),
    },
    {
        "ts": "2025-11-27T14:00:00Z",  # Week 48 — Thu (Thanksgiving)
        "title": "Thanksgiving — the whole family together",
        "body": (
            "My parents drove up from Charlotte, my sister and her family flew in from "
            "Denver. Thirteen people around the table — first time we've all been "
            "together in two years. Mom made her cornbread stuffing, I handled the "
            "turkey (dry-brine, spatchcocked — came out great), and my sister brought "
            "two pies. The kids ran around the yard until dark while the adults caught "
            "up over wine by the fireplace. Nobody argued about anything. Dad looked "
            "healthier than he has in years. Grateful in the most straightforward, "
            "uncomplicated way I've felt in a long time."
        ),
    },
    # ── December 2025 ─────────────────────────────────────────────────────────
    {
        "ts": "2025-12-03T10:00:00Z",  # Week 49 — Wed
        "title": "Merged the notification service refactor",
        "body": (
            "After six weeks of work the notification service PR finally merged today. "
            "It replaces the old synchronous email-sending code with an async queue "
            "backed by SQS, adds retry logic with exponential backoff, and drops the "
            "third-party SDK we'd been carrying since 2019. The diff was 3,400 lines — "
            "not my proudest moment size-wise, but the scope was unavoidable. "
            "Code review took two weeks. Staging tests all passed. Deployed to prod "
            "with a feature flag and monitored for an hour. Everything green. "
            "Closed 17 open issues in one shot. Genuinely satisfying."
        ),
    },
    {
        "ts": "2025-12-14T21:00:00Z",  # Week 50 — Sun
        "title": "Anniversary dinner",
        "body": (
            "Twelve years. We got a babysitter and went back to the restaurant where "
            "we had our first date — same little bistro, same corner table, somehow "
            "still the same menu. We ordered the same things we ordered back then just "
            "for the fun of it. Talked for three hours about where we've been and where "
            "we want to go next. The kids, the house, the next chapter. She mentioned "
            "wanting to take a proper trip without the children — somewhere warm in "
            "February. I'm already looking at flights. Grateful for her, for us, "
            "for the ordinary miracle of twelve years."
        ),
    },
    {
        "ts": "2025-12-22T16:00:00Z",  # Week 52 — Mon
        "title": "Year-end team retrospective",
        "body": (
            "Ran our annual retrospective with the full engineering team today — "
            "twenty people, three hours, good coffee. We used a structured format: "
            "what went well, what we'd do differently, what to carry forward. "
            "Top wins: zero severity-1 incidents in Q3, the migration to the new "
            "deployment pipeline, and a huge improvement in PR review turnaround. "
            "Top regrets: we didn't invest enough in documentation, and onboarding "
            "new engineers still takes too long. I left with a list of five concrete "
            "process changes to pilot in Q1. Good way to close out the year."
        ),
    },
    {
        "ts": "2025-12-31T23:30:00Z",  # Week 1 — Wed (NYE)
        "title": "New Year's Eve — reflections",
        "body": (
            "Sitting on the back porch with a glass of bourbon while the kids watch "
            "the countdown on TV inside. 2025 was a full year. Professionally: shipped "
            "meaningful work, grew as a technical leader, stayed curious. Personally: "
            "more present than the year before, made it to almost all of Liam's games, "
            "read 14 books. Health: ran my first 10K in October, started doing "
            "yoga twice a week. Things I want for 2026: less reactivity, more "
            "intentionality, a real vacation. The fireworks just started in the distance. "
            "Here we go."
        ),
    },
    # ── January 2026 ──────────────────────────────────────────────────────────
    {
        "ts": "2026-01-05T08:00:00Z",  # Week 2 — Mon
        "title": "Back to work — Q1 kickoff",
        "body": (
            "First day back after the holiday break. The office felt quieter than usual "
            "with a few people still on PTO. Spent the morning clearing two weeks of "
            "email — flagged 12 things, deleted 200, actually replied to 6. In the "
            "afternoon we had the Q1 kickoff with leadership. Big themes: reliability "
            "first, then velocity. They want us to hit 99.9% API uptime and reduce "
            "incident response time further. Also announced a new team forming around "
            "developer productivity tooling. I've been asked to contribute 20% time. "
            "Interesting. Ended the day feeling re-energized despite the email mountain."
        ),
    },
    {
        "ts": "2026-01-17T19:00:00Z",  # Week 3 — Sat
        "title": "Family board game weekend",
        "body": (
            "Declared this a screens-off Saturday. We pulled out every board game we "
            "own and let the kids pick the order. Ticket to Ride, Codenames, Sushi Go, "
            "and one chaotic round of Blokus. Emma took Codenames very seriously and "
            "gave clues so cryptic that none of us got them — she thought this was "
            "hilarious. Liam dominated Ticket to Ride with a long-route strategy nobody "
            "expected from an eight-year-old. We ordered pizza for dinner and kept "
            "playing until 9 pm. These are the days I want to remember when the kids "
            "are grown and gone."
        ),
    },
    {
        "ts": "2026-01-27T11:30:00Z",  # Week 5 — Tue
        "title": "On-call rotation — navigating a database incident",
        "body": (
            "Got paged at 2 am — primary database replica fell behind by 45 minutes "
            "and reads were timing out for about 8% of users. Spent 90 minutes "
            "diagnosing: a batch job had triggered a full table scan that locked "
            "rows. Killed the job, waited for replication to catch up, confirmed "
            "metrics returned to normal by 4 am. Wrote the incident report in the "
            "morning while still groggy. Root cause: the batch job was added without "
            "a proper review of its query plan. Action items: mandatory EXPLAIN ANALYZE "
            "for any new DML touching tables over 10M rows. On-call is humbling."
        ),
    },
    # ── February 2026 ─────────────────────────────────────────────────────────
    {
        "ts": "2026-02-07T20:00:00Z",  # Week 6 — Sat
        "title": "Costa Rica — Day 1",
        "body": (
            "We actually did it. Booked in December, talked about it for weeks, and "
            "now we're here — just the two of us, no kids. The flight landed in San José "
            "mid-morning and we drove straight to the Arenal area. The volcano was "
            "fully visible on the drive in — dramatic and calm at the same time. "
            "Checked into a small lodge surrounded by cloud forest. Heard howler monkeys "
            "within five minutes of arriving. Spent the evening on the deck with "
            "ceviche and cold Imperials watching the sun drop behind the ridge. "
            "My nervous system is already unwinding."
        ),
    },
    {
        "ts": "2026-02-09T18:30:00Z",  # Week 7 — Mon
        "title": "Costa Rica — zip-lining and hot springs",
        "body": (
            "Full adventure day. Zip-lined across the forest canopy in the morning — "
            "eleven cables, the longest nearly a kilometre. She screamed on every one; "
            "I pretended not to. After lunch we hiked a trail that cuts through old "
            "lava fields from the 1968 eruption — eerie and beautiful. Finished at "
            "the hot springs near the base of Arenal. Soaked for two hours while "
            "the volcano loomed above us in the dark. No phones, no laptops, no "
            "meetings. Can't remember the last time I felt this rested. Two more days "
            "before we fly home — going to make every hour count."
        ),
    },
    {
        "ts": "2026-02-24T17:00:00Z",  # Week 9 — Tue
        "title": "Knowledge-sharing session: observability patterns",
        "body": (
            "Ran a two-hour internal workshop on observability — structured logs, "
            "distributed tracing, and alerting philosophy. About 25 engineers attended, "
            "mix of senior and junior. I used real examples from our own incidents to "
            "show what good telemetry looks like versus what we had before last year's "
            "improvements. Got a lot of questions about trace sampling strategies and "
            "cost management. One engineer asked about OpenTelemetry adoption — "
            "that's probably a separate session. Will turn the slides and notes into "
            "a Confluence doc this week. Teaching is one of the best ways I know "
            "to solidify my own understanding."
        ),
    },
    # ── March 2026 ────────────────────────────────────────────────────────────
    {
        "ts": "2026-03-08T21:00:00Z",  # Week 10 — Sun
        "title": "Planning Liam's birthday camping trip",
        "body": (
            "Liam turns nine in three weeks and his one wish is a camping trip with "
            "his two best friends. Spent the evening mapping it out: Shenandoah for "
            "two nights, s'mores mandatory, a short hike with a waterfall at the end. "
            "Coordinated with the other parents over text — everyone's in. Pulled out "
            "the camping gear from the garage and made a checklist: sleeping bags need "
            "airing out, the camp stove needs a new fuel canister, and I should "
            "probably replace the headlamp that's been dying for two years. "
            "Liam is going to love this. I'm already looking forward to it more than "
            "I'm willing to admit to a nine-year-old."
        ),
    },
]


# ── DynamoDB helpers ──────────────────────────────────────────────────────────

def _build_resource():
    kwargs = {
        "region_name": REGION,
        "config": Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 2}),
    }
    if ENDPOINT:
        kwargs["endpoint_url"] = ENDPOINT
        # Local mode — mocked credentials so boto3 doesn't complain
        kwargs.setdefault("aws_access_key_id", "local")
        kwargs.setdefault("aws_secret_access_key", "local")
    return boto3.resource("dynamodb", **kwargs)


def _ensure_table(ddb):
    """Create table if missing (local only — AWS tables should be pre-provisioned)."""
    try:
        ddb.create_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"  Created table '{TABLE_NAME}'.")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceInUseException":
            print(f"  Table '{TABLE_NAME}' already exists — OK.")
        else:
            raise


def _put_entry(table, entry_id: str, ts: str, title: str, body: str):
    pk = f"USER#{USER_ID}"
    sk = f"ENTRY#{ts}#{entry_id}"

    # Main item
    table.put_item(Item={
        "PK": pk,
        "SK": sk,
        "entityType": "JOURNAL_ENTRY",
        "entryId": entry_id,
        "userId": USER_ID,
        "title": title,
        "body": body,
        "createdAt": ts,
        "updatedAt": ts,
        "aiStatus": "NOT_REQUESTED",
        "tags": [],
    })

    # Lookup item (needed by resolve_entry / get_entry)
    table.put_item(Item={
        "PK": pk,
        "SK": f"ENTRYID#{entry_id}",
        "entityType": "ENTRY_LOOKUP",
        "entryId": entry_id,
        "entrySk": sk,
        "createdAt": ts,
    })


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    mode = f"local ({ENDPOINT})" if ENDPOINT else f"AWS ({REGION})"
    print(f"\nSeed target : {mode}")
    print(f"Table       : {TABLE_NAME}")
    print(f"User        : {USER_ID}")
    print(f"Entries     : {len(ENTRIES)}\n")

    ddb = _build_resource()

    if ENDPOINT:
        print("Local mode — ensuring table exists...")
        _ensure_table(ddb)

    table = ddb.Table(TABLE_NAME)

    for i, e in enumerate(ENTRIES, 1):
        entry_id = str(uuid.uuid4())
        _put_entry(table, entry_id, e["ts"], e["title"], e["body"])
        date_part = e["ts"][:10]
        print(f"  [{i:02d}/{len(ENTRIES)}] {date_part}  {e['title']}")

    total = len(ENTRIES)
    print(f"\nDone — {total} entries seeded for user '{USER_ID}'.")
    print("Run 'docker compose up' then visit http://localhost:3000 to see them.")
    print("Generate AI insights via: POST /insights/summaries\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
