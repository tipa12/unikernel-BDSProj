# MirageOS

## Docker setup

Build this image using `docker build --progress plain -t bdspro-mirageos .`

## Examples

- <https://github.com/mirage/mirage-skeleton>
- <https://github.com/tarides/unikernels>
- <https://github.com/roburio/unikernels>

## Hello setup

Prerequisite: `git clone https://github.com/mirage/mirage-skeleton`

1. Navigate to ```mirage-skeleton/hello```
2. Configure `mirage configure -t unix`
3. Install external dependencies `make depends`
4. Build using `make`
5. Run the application `./dist/hello`
