# Backdrop Club loader

Draws a backdrop behind your conversation in the Claude desktop app, picked from the community gallery at https://backdrop-club.netlify.app/. Every theme has a light and a dark look, sits low in the window so your chat stays readable, and is checked against an allow-list of drawing elements before it is published and again before it is drawn.

- `/backdrop <name>` switches to a theme from the gallery
- `/backdrop random` picks one for you
- `/backdrop list [tag]` lists the gallery
- `/backdrop off` and `/backdrop on` hide and restore it

Your pick is kept across sessions. A bundled scene shows until you pick one, so it works offline too.
