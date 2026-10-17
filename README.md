# starplot-milkyway

Milky Way catalog builder for [Starplot](https://github.com/steveberardi/starplot).

1. `make install` to create virtual environment
2. `make build` to build catalog files
3. `make release` to create release (only run from GitHub action)

## Building a new release

1. Ensure version doesn't already exist
2. Run "Publish Release" GitHub action (this will run build and then create the GH tagged release)
