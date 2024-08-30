import os

def filter_important_files(file_paths):
    """
    Filter a list of file paths to return only those that are commonly important in codebases.
    
    :param file_paths: List of file paths to check
    :return: List of file paths that match important file patterns
    """
    important_files = [
        # Version Control
        '.gitignore', '.gitattributes',
        # Package Management and Dependencies
        'requirements.txt', 'Pipfile', 'pyproject.toml', 'package.json', 'package-lock.json', 'yarn.lock',
        'Gemfile', 'Gemfile.lock', 'composer.json', 'composer.lock', 'pom.xml', 'build.gradle', 'go.mod', 'go.sum',
        # Project Configuration
        '.editorconfig', '.eslintrc', '.pylintrc', 'tsconfig.json',
        # Build and Compilation
        'Makefile', 'webpack.config.js', 'gulpfile.js',
        # CI/CD
        '.travis.yml', '.gitlab-ci.yml', 'Jenkinsfile',
        # Docker
        'Dockerfile', 'docker-compose.yml',
        # Environment Variables
        '.env', '.env.example',
        # Deployment
        'Procfile', 'vercel.json', 'netlify.toml', 'app.yaml',
        # Documentation
        'README.md', 'CONTRIBUTING.md', 'LICENSE', 'CHANGELOG.md',
        # Language-specific
        'setup.py', '__init__.py', 'Rakefile', '.babelrc', '.npmrc', '.htaccess',
        # Framework-specific
        'manage.py', 'settings.py', 'routes.rb',
        # Testing
        'pytest.ini', 'phpunit.xml', 'karma.conf.js',
        # Security
        '.npmrc', '.pypirc'
    ]
    
    def is_important(file_path):
        file_name = os.path.basename(file_path)
        return file_name in important_files or any(file_path.endswith(f'/{name}') for name in important_files)
    
    return list(filter(is_important, file_paths))
