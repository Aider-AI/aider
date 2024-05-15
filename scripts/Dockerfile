# Use the official Jekyll image from Docker Hub
FROM jekyll/jekyll:latest

# Set the working directory
WORKDIR /srv/jekyll

# Copy the current directory contents into the container at /srv/jekyll
COPY . /srv/jekyll

# Install any needed packages specified in Gemfile
RUN bundle install

# Expose port 4000 to the host
EXPOSE 4000

# Run Jekyll server
CMD ["jekyll", "serve", "--host", "0.0.0.0"]
