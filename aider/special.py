import os

IMPORTANT_FILES = [
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
    "Makefile",
    "CMakeLists.txt",
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
    "conftest.py",
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
    "manage.py",
    "settings.py",  # Django
    "config/routes.rb",
    "Rakefile",  # Ruby on Rails
    "next.config.js",
    "nuxt.config.js",  # Next.js, Nuxt.js
    "vue.config.js",
    "angular.json",  # Vue.js, Angular
    "gatsby-config.js",
    "gridsome.config.js",  # Gatsby, Gridsome
    # API Documentation
    "swagger.yaml",
    "swagger.json",
    "openapi.yaml",
    "openapi.json",
    # Language-specific
    "__init__.py",  # Python
    "stack.yaml",
    "package.yaml",  # Haskell
    ".htaccess",  # Apache
    ".bowerrc",  # Bower
    # Development environment
    ".nvmrc",
    ".ruby-version",
    ".python-version",
    "Vagrantfile",
    # Quality and metrics
    ".codeclimate.yml",
    ".coveragerc",
    "codecov.yml",
    # Documentation
    "mkdocs.yml",
    "_config.yml",
    "book.toml",
    "docs/conf.py",
    "readthedocs.yml",
    ".readthedocs.yaml",
    # Package registries
    ".npmrc",
    ".yarnrc",
    # IDE and Editor
    ".vscode/settings.json",
    ".idea/workspace.xml",
    ".sublime-project",
    ".vim",
    "_vimrc",
    # Linting and formatting
    ".isort.cfg",
    ".markdownlint.json",
    ".markdownlint.yaml",
    # Security
    ".bandit",
    ".secrets.baseline",
    # Misc
    "CODEOWNERS",
    ".pypirc",
    ".gitkeep",
    ".npmignore",
]


# Normalize IMPORTANT_FILES once
NORMALIZED_IMPORTANT_FILES = [os.path.normpath(path) for path in IMPORTANT_FILES]


def is_important(file_path):
    file_name = os.path.basename(file_path)
    dir_name = os.path.dirname(file_path)

    # Check for GitHub Actions workflow files
    if (
        os.path.basename(dir_name) == "workflows"
        and os.path.basename(os.path.dirname(dir_name)) == ".github"
        and file_name.endswith(".yml")
    ):
        return True

    # Check for IDE-specific directories
    if file_name in [".idea", ".vscode"]:
        return True

    """
    # Check for Kubernetes config files
    if "kubernetes" in os.path.normpath(dir_name).split(os.sep) and file_name.endswith(".yaml"):
        return True

    # Check for migration directories
    if file_name == "migrations" and os.path.isdir(file_path):
        return True
    """

    # Check if the file_path matches any of the NORMALIZED_IMPORTANT_FILES
    normalized_path = os.path.normpath(file_path)
    return any(
        normalized_path == important_file or normalized_path.endswith(os.sep + important_file)
        for important_file in NORMALIZED_IMPORTANT_FILES
    )


def filter_important_files(file_paths):
    """
    Filter a list of file paths to return only those that are commonly important in codebases.

    :param file_paths: List of file paths to check
    :return: List of file paths that match important file patterns
    """
    return list(filter(is_important, file_paths))
