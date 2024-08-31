import os

ROOT_IMPORTANT_FILES = [
    # Version Control
    ".gitignore",
    ".gitattributes",
    # Documentation
    "README",
    "README.md",
    "README.txt",
    "README.rst",
    "CONTRIBUTING",
    "CONTRIBUTING.md",
    "CONTRIBUTING.txt",
    "CONTRIBUTING.rst",
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "CHANGELOG",
    "CHANGELOG.md",
    "CHANGELOG.txt",
    "CHANGELOG.rst",
    "SECURITY",
    "SECURITY.md",
    "SECURITY.txt",
    "CODEOWNERS",
    # Package Management and Dependencies
    "requirements.txt",
    "Pipfile",
    "Pipfile.lock",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "npm-shrinkwrap.json",
    "Gemfile",
    "Gemfile.lock",
    "composer.json",
    "composer.lock",
    "pom.xml",
    "build.gradle",
    "build.sbt",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "mix.exs",
    "rebar.config",
    "project.clj",
    "Podfile",
    "Cartfile",
    "dub.json",
    "dub.sdl",
    # Configuration and Settings
    ".env",
    ".env.example",
    ".editorconfig",
    "tsconfig.json",
    "jsconfig.json",
    ".babelrc",
    "babel.config.js",
    ".eslintrc",
    ".eslintignore",
    ".prettierrc",
    ".stylelintrc",
    "tslint.json",
    ".pylintrc",
    ".flake8",
    ".rubocop.yml",
    ".scalafmt.conf",
    ".dockerignore",
    ".gitpod.yml",
    "sonar-project.properties",
    "renovate.json",
    "dependabot.yml",
    ".pre-commit-config.yaml",
    "mypy.ini",
    "tox.ini",
    ".yamllint",
    "pyrightconfig.json",
    # Build and Compilation
    "webpack.config.js",
    "rollup.config.js",
    "parcel.config.js",
    "gulpfile.js",
    "Gruntfile.js",
    "build.xml",
    "build.boot",
    "project.json",
    "build.cake",
    "MANIFEST.in",
    # Testing
    "pytest.ini",
    "phpunit.xml",
    "karma.conf.js",
    "jest.config.js",
    "cypress.json",
    ".nycrc",
    ".nycrc.json",
    # CI/CD
    ".travis.yml",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "appveyor.yml",
    "circle.yml",
    ".circleci/config.yml",
    ".github/dependabot.yml",
    "codecov.yml",
    ".coveragerc",
    # Docker and Containers
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.override.yml",
    # Cloud and Serverless
    "serverless.yml",
    "firebase.json",
    "now.json",
    "netlify.toml",
    "vercel.json",
    "app.yaml",
    "terraform.tf",
    "main.tf",
    "cloudformation.yaml",
    "cloudformation.json",
    "ansible.cfg",
    "kubernetes.yaml",
    "k8s.yaml",
    # Database
    "schema.sql",
    "liquibase.properties",
    "flyway.conf",
    # Framework-specific
    "next.config.js",
    "nuxt.config.js",
    "vue.config.js",
    "angular.json",
    "gatsby-config.js",
    "gridsome.config.js",
    # API Documentation
    "swagger.yaml",
    "swagger.json",
    "openapi.yaml",
    "openapi.json",
    # Development environment
    ".nvmrc",
    ".ruby-version",
    ".python-version",
    "Vagrantfile",
    # Quality and metrics
    ".codeclimate.yml",
    "codecov.yml",
    # Documentation
    "mkdocs.yml",
    "_config.yml",
    "book.toml",
    "readthedocs.yml",
    ".readthedocs.yaml",
    # Package registries
    ".npmrc",
    ".yarnrc",
    # Linting and formatting
    ".isort.cfg",
    ".markdownlint.json",
    ".markdownlint.yaml",
    # Security
    ".bandit",
    ".secrets.baseline",
    # Misc
    ".pypirc",
    ".gitkeep",
    ".npmignore",
]


# Normalize the lists once
NORMALIZED_ROOT_IMPORTANT_FILES = set(os.path.normpath(path) for path in ROOT_IMPORTANT_FILES)


def is_important(file_path):
    file_name = os.path.basename(file_path)
    dir_name = os.path.normpath(os.path.dirname(file_path))
    normalized_path = os.path.normpath(file_path)

    # Check for GitHub Actions workflow files
    if dir_name == os.path.normpath(".github/workflows") and file_name.endswith(".yml"):
        return True

    return normalized_path in NORMALIZED_ROOT_IMPORTANT_FILES


def filter_important_files(file_paths):
    """
    Filter a list of file paths to return only those that are commonly important in codebases.

    :param file_paths: List of file paths to check
    :return: List of file paths that match important file patterns
    """
    return list(filter(is_important, file_paths))
