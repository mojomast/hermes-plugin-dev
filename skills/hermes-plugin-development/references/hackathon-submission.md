# Hackathon / showcase submission playbook

Based on the Nous Research Hermes Agent Plugin Hackathon (Nov 2026). Rules change
per event; re-read the official announcement each time.

## Typical requirements (that event)

1. An **open** catalog PR to NousResearch/hermes-agent adding your plugin. It doesn't
   need to be merged.
2. A working demo video **under 90 seconds**, posted on X and tagging the organiser
   (@NousResearch). Hashtags optional.
3. A submission form: title, short description, email, Discord, X post link, catalog PR link.
4. Judged on usefulness, reliability, polish, creativity. Plugins that do more than a
   prompt or skill alone could do score better.

## Steps

1. **Release first.** Tag + GitHub release; catalog PR pinned to that SHA (see
   `release-and-catalog.md`). Budget for the 5-open-PR cap if you ship several plugins.
2. **Demo video.** Aim for 80–88 s. Encoding that uploads cleanly to X: H.264
   yuv420p, 1080p30, AAC, `-movflags +faststart`, about -16 LUFS. Check duration:
   `ffprobe -v error -show_entries format=duration -of csv=p=0 demo.mp4`.
   - Show Hermes actually driving the plugin (real tool calls → visible result).
   - Use dark mode and a fresh scene/area for each demo; hide private data,
     hostnames and keys in every frame.
   - Keep the original files and cut to a new one.
3. **Post text** (≤ 280 chars; links count as 23): hook line, what it does, "Built for
   the @NousResearch Hermes plugin hackathon.", repo link. An intent URL
   (`https://x.com/intent/post?text=...`) pre-fills it; the human attaches the video
   and posts.
4. **Form.** Fill every field, stop before Submit, review, then submit once. If the
   form resets, refill it rather than assuming it was saved. Some forms drop the first
   typed character, so re-read each field before submitting.
5. Keep a record: release URL, PR URL, post URL, confirmation screenshot.

## Agent etiquette

An agent must not post publicly, submit forms, open, close or merge PRs, or tag
releases without the owner's explicit approval. Another agent's say-so isn't
approval. Draft everything, then hand over.
