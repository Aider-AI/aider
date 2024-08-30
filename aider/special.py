import os

IMPORTANT_FILES = [
    # Version Control
    ".gitignore",
    ".gitattributes",
    # Documentation
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CODEOWNERS",
    # Package Management and Dependencies
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "setup.py",
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
    # Testing
    "pytest.ini",
    "phpunit.xml",
    "karma.conf.js",
    "jest.config.js",
    "cypress.json",
    # CI/CD
    ".travis.yml",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "appveyor.yml",
    "circle.yml",
    ".circleci/config.yml",
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
    # Package registries
    ".npmrc",
    ".yarnrc",
    # IDE and Editor
    ".vscode/settings.json",
    ".idea/workspace.xml",
    ".sublime-project",
    ".vim",
    "_vimrc",
    # Misc
    "CODEOWNERS",
    ".pypirc",
]


def filter_important_files(file_paths):
    """
    Filter a list of file paths to return only those that are commonly important in codebases.

    :param file_paths: List of file paths to check
    :return: List of file paths that match important file patterns
    """

    def is_important(file_path):
        file_name = os.path.basename(file_path)
        dir_name = os.path.dirname(file_path)

        # Check for GitHub Actions workflow files
        if dir_name.endswith(".github/workflows") and file_name.endswith(".yml"):
            return True

        # Check for IDE-specific directories
        if file_name in [".idea", ".vscode"]:
            return True

        # Check for Kubernetes config files
        if "kubernetes" in dir_name.split(os.path.sep) and file_name.endswith(".yaml"):
            return True

        # Check for migration directories
        if file_name == "migrations" and os.path.isdir(file_path):
            return True

        return file_name in IMPORTANT_FILES or any(
            file_path.endswith(f"/{name}") for name in IMPORTANT_FILES
        )

    return list(filter(is_important, file_paths))
