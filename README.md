# Polynesia Connect — sitemap

*[Version française plus bas](#version-française)*

Automatic XML sitemap for [www.polynesiaconnect.com](https://www.polynesiaconnect.com), rebuilt every **Monday and Thursday** by GitHub Actions, then copied to the site itself by the "PC Sitemap Sync" widget (page `/pc-sitemap-sync`, secret token) so Google and Bing accept it:

**https://www.polynesiaconnect.com/filedata/cache/sitemaps/sitemap.xml** (also reachable as `/sitemap.xml`, 301)

A copy stays on GitHub Pages: https://patryk-hd.github.io/polynesiaconnect-sitemap/sitemap.xml

`crawl.py` visits the site like a search engine (politely: 4 requests at a time) and keeps only the pages that load, are indexable and are their own canonical page: business profiles, events, jobs, classifieds, real estate, categories, cities and static pages. Location × category combination pages, account pages, empty sections and personal accounts are left out. `lastmod` is the day a page's title, description or main heading last changed (`state.json`).

The site's `robots.txt` points to the copy on the site. `changes.json` lists the pages added, changed and removed by the last run.

Run by hand: Actions → Sitemap → Run workflow. Locally: `python3 crawl.py`.

---

## Version française

Sitemap XML automatique de [www.polynesiaconnect.com](https://www.polynesiaconnect.com), reconstruit chaque **lundi et jeudi** par GitHub Actions, puis copié sur le site par le widget « PC Sitemap Sync » (page `/pc-sitemap-sync`, jeton secret) pour que Google et Bing l'acceptent :

**https://www.polynesiaconnect.com/filedata/cache/sitemaps/sitemap.xml** (aussi accessible par `/sitemap.xml`, 301)

Une copie reste sur GitHub Pages : https://patryk-hd.github.io/polynesiaconnect-sitemap/sitemap.xml

`crawl.py` parcourt le site comme un moteur de recherche (poliment : 4 requêtes à la fois) et ne garde que les pages qui s'affichent, indexables et canoniques : fiches entreprises, événements, offres d'emploi, annonces, immobilier, catégories, communes et pages fixes. Les pages de combinaisons lieu × catégorie, les pages de compte, les rubriques vides et les comptes de particuliers sont exclus. `lastmod` = le jour où le titre, la description ou le titre principal de la page a changé (`state.json`).

Le `robots.txt` du site pointe vers la copie sur le site. `changes.json` liste les pages ajoutées, modifiées et retirées au dernier passage.

Lancer à la main : Actions → Sitemap → Run workflow. En local : `python3 crawl.py`.
