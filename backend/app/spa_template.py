"""
SPA Template for serving SvelteKit applications
"""


def get_spa_html_template(css_files, start_js):
    """
    Generate an HTML template for serving SvelteKit applications

    Args:
        css_files: List of CSS file paths
        start_js: Path to the start.js file

    Returns:
        HTML template as a string
    """
    # Build CSS links
    css_links = ""
    for css_file in css_files:
        css_links += (
            f'<link rel="stylesheet" href="/_app/immutable/assets/{css_file.name}">\n'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <link rel="icon" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Cointainr</title>
    {css_links}
</head>
<body data-sveltekit-preload-data="hover">
    <div style="display: contents">
        <div id="svelte"></div>
    </div>
    
    <script type="module">
        import * as module from '/_app/immutable/entry/{start_js}';
        
        if (module.start) {{
            module.start({{
                paths: {{
                    base: "",
                    assets: ""
                }},
                target: document.getElementById('svelte'),
                version: "",
                env: {{}}
            }});
        }}
    </script>
</body>
</html>"""
