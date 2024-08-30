import os


def filter_important_files(file_paths):
    """
    Filter a list of file paths to return only those that are commonly important in codebases.

    :param file_paths: List of file paths to check
    :return: List of file paths that match important file patterns
    """
    important_files = [
        # Version Control
        ".gitignore", ".gitattributes",
        # Package Management and Dependencies
        "requirements.txt", "Pipfile", "pyproject.toml", "package.json", "package-lock.json",
        "yarn.lock", "Gemfile", "Gemfile.lock", "composer.json", "composer.lock", "pom.xml",
        "build.gradle", "go.mod", "go.sum",
        # Project Configuration
        ".editorconfig", ".eslintrc", ".pylintrc", "tsconfig.json",
        # Build and Compilation
        "Makefile", "webpack.config.js", "gulpfile.js",
        # CI/CD
        ".travis.yml", ".gitlab-ci.yml", "Jenkinsfile",
        # Docker
        "Dockerfile", "docker-compose.yml",
        # Environment Variables
        ".env", ".env.example",
        # Deployment
        "Procfile", "vercel.json", "netlify.toml", "app.yaml",
        # Documentation
        "README.md", "CONTRIBUTING.md", "LICENSE", "CHANGELOG.md",
        # Language-specific
        "setup.py", "__init__.py", "Rakefile", ".babelrc", ".npmrc", ".htaccess",
        # Framework-specific
        "manage.py", "settings.py", "routes.rb",
        # Testing
        "pytest.ini", "phpunit.xml", "karma.conf.js",
        # Security
        ".npmrc", ".pypirc",
        # New entries
        "Cargo.toml", "Cargo.lock", "build.sbt", "stack.yaml", "package.yaml",
        "mix.exs", "project.clj", ".prettierrc", ".stylelintrc", "tslint.json",
        "babel.config.js", "jest.config.js", "cypress.json", "serverless.yml",
        "firebase.json", "now.json", "docker-compose.override.yml", "schema.sql",
        "next.config.js", "nuxt.config.js", "vue.config.js", "angular.json",
        "swagger.yaml", "swagger.json", "openapi.yaml", "openapi.json",
        ".flake8", ".rubocop.yml", ".scalafmt.conf", "SECURITY.md", "CODEOWNERS",
    ]

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

        return file_name in important_files or any(
            file_path.endswith(f"/{name}") for name in important_files
        )

    return list(filter(is_important, file_paths))
