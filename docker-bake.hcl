## https://docs.docker.com/build/bake/
## https://docs.docker.com/reference/cli/docker/buildx/bake/#set
## https://github.com/crazy-max/buildx#remote-with-local
## https://github.com/docker/metadata-action

variable "UV_DEFAULT_INDEX" {
    default = "https://mirrors.huaweicloud.com/repository/pypi/simple"
}

variable "GITHUB_PROXY" {
    default = "https://fastfile.asfd.cn/"
}

## Special target: https://github.com/docker/metadata-action#bake-definition
target "docker-metadata-action" {}

target "_image" {
    inherits = ["docker-metadata-action"]
}

target "_common" {
    labels = {
        "org.opencontainers.image.source" = "https://git.jetsung.com/idev/file-downloader"
        "org.opencontainers.image.documentation" = "https://git.jetsung.com/idev/file-downloader"
        "org.opencontainers.image.authors" = "Jetsung Chan<i@jetsung.com>"
    }
    context = "."
    dockerfile = "docker/Dockerfile"
    platforms = ["linux/amd64"]
    no-cache = true
}

target "default" {
    inherits = ["_common"]
    args = {
        UV_DEFAULT_INDEX = "${UV_DEFAULT_INDEX}"
        GITHUB_PROXY = "${GITHUB_PROXY}"
    }    
    tags = [
      "file-downloader:local",
    ]
}

group "dev" {
  targets = ["dev-amd64", "dev-arm64"]
}

target "dev" {
    inherits = ["_common", "_image"]
}

target "dev-amd64" {
    inherits = ["_common", "_image"]
    platforms = ["linux/amd64"]
}

target "dev-arm64" {
    inherits = ["_common", "_image"]
    platforms = ["linux/arm64"]
}

group "release" {
  targets = ["release"]
}

target "release" {
    inherits = ["_common", "_image"]
    platforms = ["linux/amd64","linux/arm64"]
}