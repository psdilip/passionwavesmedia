# Passionwaves Media

A static site you write in Markdown. Run one command, upload one folder. No HTML editing, no servers, no pip installs.

## Folder map

```
site.json         ← all your settings + homepage copy (edit this)
content/          ← your articles, as .md files (write these)
assets/styles.css ← the look (edit rarely)
assets/app.js     ← behavior: filter, likes, views
build.py          ← run this to generate the site
public/           ← the generated site — THIS is what you upload to S3
```

## Publishing an article — the whole workflow

1. Create `content/my-new-post.md`:

   ```
   ---
   title: My new post
   slug: my-new-post
   category: Travel
   excerpt: One or two sentences shown on the card and as the subtitle.
   date: 2026-08-01
   featured: true      # optional — puts it in the big top slot
   ---

   Your article in **Markdown**. Headings with #, lists with -, quotes with >,
   `inline code`, [links](https://example.com), and images all work.
   ```

2. Run:

   ```
   python3 build.py
   ```

3. Upload everything in `public/` to your S3 bucket. Done.

`category` must match one of the categories in `site.json`. Reading time is calculated automatically. Articles sort newest-first.

## The homepage vs. the "All articles" page

The site now has two views, so a big archive never dumps onto the homepage:

- **Homepage** shows the featured piece plus the **6 most recent** articles, then a
  "Browse all articles" button. To change how many appear, edit the `[:6]` in
  `build.py` (in `build_index`).
- **articles.html** is a sidebar navigator: search (matches titles, excerpts, *and*
  tags), a category list with live counts, a sort control, and a rotating quote at
  the top of the sidebar. Everything renders client-side from a JSON blob of your
  posts embedded in the page, so filtering/search/sort are instant with no reload.
  Deep links like `articles.html#Travel` pre-select that category on load.

Both pages regenerate automatically when you run `python3 build.py`. Cards show each
article's first image (or a category-colored fallback if it has none) plus its tags.

## Adding or renaming categories

In `site.json`, edit the `categories` block — each is a name and a color. The filter chips, dots, and footer update themselves on the next build.

```json
"categories": { "AWS": "#6B4EE6", "Travel": "#22B0C4", "Music": "#3BB273" }
```

## LinkedIn & X links

In `site.json` under `social`, replace the two placeholder URLs with your real profiles. They appear in the footer with icons. Leave one blank to hide it.

## RSS feed

There's no email signup — the site publishes `feed.xml` (RSS 2.0) automatically on
every build, listing every article with its title, link, category, and excerpt. It's
linked from the header ("RSS"), the footer, and a `<link rel="alternate">` tag in
`<head>` so feed readers and browsers can auto-discover it. Anyone who wants to know
when you post can subscribe with any RSS reader — no backend, no provider account.

## Likes & views — 5-minute setup (optional)

Because the site is static, shared counts need a tiny free datastore. **Supabase**
is the easiest (no server to run). Without it, the like button still works per-browser;
view counts just stay hidden. This is already wired up for every article automatically —
`build_article()` renders the like/view widget on every post, current and future, driven
purely by the post's slug, so there's nothing extra to do per-article once this is set up.

1. Create a free project at supabase.com. Copy the Project URL and the `anon` public key
   into `site.json` → `supabase`.
2. In the Supabase SQL editor, run:

   ```sql
   create table stats (slug text primary key, likes int default 0, views int default 0);
   alter table stats enable row level security;

   create or replace function pw_view(p_slug text)
   returns table(likes int, views int) language plpgsql security definer as $$
   begin
     insert into stats(slug, views) values (p_slug, 1)
     on conflict (slug) do update set views = stats.views + 1;
     return query select s.likes, s.views from stats s where s.slug = p_slug;
   end; $$;

   create or replace function pw_like(p_slug text)
   returns table(likes int, views int) language plpgsql security definer as $$
   begin
     insert into stats(slug, likes) values (p_slug, 1)
     on conflict (slug) do update set likes = stats.likes + 1;
     return query select s.likes, s.views from stats s where s.slug = p_slug;
   end; $$;

   create or replace function pw_top_stats()
   returns table(slug text, likes int, views int) language sql security definer
   stable as $$
     select s.slug, s.likes, s.views from stats s;
   $$;

   grant execute on function pw_view(text), pw_like(text), pw_top_stats() to anon;
   ```

3. Rebuild. Likes and reads now count for real, shared across everyone. The homepage's
   "Trending" strip (Most Viewed / Most Liked) reads through `pw_top_stats()` — a
   read-only aggregate with no parameters, so there's no injection surface, same as the
   other two functions.

   **If you already ran step 2 before `pw_top_stats()` existed** (i.e. `stats`,
   `pw_view`, and `pw_like` are already set up): do **not** re-run the block above — the
   `create table stats` line will fail with `relation "stats" already exists` and stop
   the whole script before it reaches `pw_top_stats()`. Instead, run only this:

   ```sql
   create or replace function pw_top_stats()
   returns table(slug text, likes int, views int) language sql security definer
   stable as $$
     select s.slug, s.likes, s.views from stats s;
   $$;

   grant execute on function pw_top_stats() to anon;
   ```

**Why this is safe to expose publicly:**
- Row-level security is on and **no policy grants the `anon` role any direct access
  to the `stats` table** — the only way in is through the three functions below.
- The functions are `security definer` (they run with the owner's privileges to get
  past RLS on purpose). `pw_view`/`pw_like` each only run a fixed, parameterized upsert
  against one row keyed by `slug`; `pw_top_stats` takes no parameters and only reads —
  there's no dynamic SQL anywhere, so there's no injection surface.
- `grant execute` is scoped to exactly `pw_view`, `pw_like`, and `pw_top_stats`, nothing
  else — the `anon` key can't read, write, or call anything beyond those three functions.
- **Known trade-off:** there's no server-side rate limiting. The "one like per browser"
  rule is enforced client-side via `localStorage`, which stops accidental double-likes
  but not someone deliberately scripting requests against the public functions. For a
  personal blog the worst case is an inflated counter, not a data or security breach —
  but if you ever want real throttling, that means moving `pw_like`/`pw_view` behind a
  Supabase Edge Function that can check request origin/rate before writing. Ask if you
  want that built out.

## Going live on S3

1. Set your real `domain` in `site.json` and rebuild.
2. Upload the contents of `public/` to your S3 bucket (static website hosting on,
   index document `index.html`).
3. Put CloudFront in front for HTTPS + your custom domain.
