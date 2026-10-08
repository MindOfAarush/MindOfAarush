"""Render public GitHub events; publish assets without changing main history."""

import argparse
import base64
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

USER = "MindOfAarush"
REPO = f"{USER}/{USER}"
BRANCH = "profile-assets"


def api(path, method="GET", data=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-activity", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com/{path}",
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def render(user, events):
    rows = []
    labels = {"WatchEvent": "EXPLORING", "PullRequestEvent": "PULL REQUEST", "IssuesEvent": "ISSUE", "PushEvent": "PUSH", "ReleaseEvent": "RELEASE"}
    seen = set()
    for event in events:
        repo = event.get("repo", {}).get("name", "")
        kind = event.get("type")
        if repo == REPO or not event.get("public", True) or kind not in labels or repo in seen:
            continue
        seen.add(repo)
        rows.append((labels[kind], repo, event.get("created_at", "")[:10]))
        if len(rows) == 3:
            break
    now = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="270" viewBox="0 0 960 270" role="img" aria-labelledby="title desc">
<title id="title">Around my GitHub</title><desc id="desc">Real public profile data and recent public events. Exploring means starred, not a coding contribution.</desc>
<rect width="960" height="270" rx="8" fill="#090909"/>
<rect x=".5" y=".5" width="959" height="269" rx="8" fill="none" stroke="#292929"/>
<g font-family="Arial, sans-serif"><text x="32" y="35" fill="#949494" font-size="11" letter-spacing="3">PUBLIC SIGNAL / AROUND MY GITHUB</text>
<text x="32" y="78" fill="#eee" font-family="Georgia, serif" font-size="28">A few things I’m exploring.</text>
<text x="928" y="35" text-anchor="end" fill="#949494" font-size="11">{html.escape(now)}</text>
<text x="928" y="76" text-anchor="end" fill="#aaa" font-size="12">{int(user.get('public_repos', 0))} public repositories · {int(user.get('followers', 0))} followers</text>
<path d="M32 100H928" stroke="#292929"/>''']
    for index, (label, repo, date) in enumerate(rows):
        y = 134 + index * 38
        parts.append(f'<text x="32" y="{y}" fill="#888" font-size="10" letter-spacing="1">{label}</text><text x="184" y="{y}" fill="#ddd" font-size="14">{html.escape(repo)}</text><text x="928" y="{y}" text-anchor="end" fill="#888" font-size="11">{html.escape(date)}</text>')
    if not rows:
        parts.append('<text x="32" y="148" fill="#aaa" font-size="14">No recent public events in GitHub’s available feed.</text>')
    parts.append('<text x="32" y="247" fill="#777" font-size="10">Public events only · Stars indicate exploration, not coding contributions · Refreshed twice a week</text></g></svg>')
    return "\n".join(parts)


def publish(content):
    try:
        api(f"repos/{REPO}/git/ref/heads/{BRANCH}")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        main = api(f"repos/{REPO}/git/ref/heads/main")
        api(f"repos/{REPO}/git/refs", "POST", {"ref": f"refs/heads/{BRANCH}", "sha": main["object"]["sha"]})
    path = f"repos/{REPO}/contents/activity.svg"
    payload = {"message": "Refresh public activity artwork", "branch": BRANCH, "content": base64.b64encode(content.encode()).decode()}
    try:
        current = api(f"{path}?ref={BRANCH}")
        if base64.b64decode(current["content"]).decode() == content:
            return
        payload["sha"] = current["sha"]
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    api(path, "PUT", payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    artwork = render(api(f"users/{USER}"), api(f"users/{USER}/events/public?per_page=100"))
    Path("activity.svg").write_text(artwork, encoding="utf-8")
    if args.publish:
        publish(artwork)
