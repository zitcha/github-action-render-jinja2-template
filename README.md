
> :warning: **This is a *public* repository** :warning:

Custom Github Actions must be in a public repository (Except when using Github Enterprise which allows private repositories)

### Github Action - Render Jinja2 Template

This is a custom Github Action used to render a Jinja2 Template.

NOTE: the rendering of the template does contain some logic specific to Zitcha

#### Example

```yaml
    steps:
      - name: Checkout
        uses: actions/checkout@v3
        
      - name: Render J2 Template
        uses: zitcha/github-action-render-jinja2-template@v1.0.0
        with:
          env-name: dev
          template-file-path: my-template.j2
          output-file-path: my-output.txt
```
