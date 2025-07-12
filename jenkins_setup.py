#2. Jenkins Credentials Setup
A#. GitHub Credentials
In Jenkins dashboard, go to Credentials > System > Global credentials

Click Add Credentials

Select:

Kind: Username with password

Scope: Global

ID: github-credentials

Username: Your GitHub username

Password: GitHub personal access token (with repo permissions)

#B. Docker Hub Credentials
Same credentials section

Add new credential:

Kind: Username with password

ID: dockerhub-creds

Username: ogegak2003

Password: Your Docker Hub password/access token

#C. Kubernetes Config (if applicable)
Add new credential:

Kind: Secret file

ID: kube-config

File: Upload your kubeconfig file

3. Jenkins Pipeline Setup
A. Create New Pipeline Job
Go to New Item > Pipeline

Name: myapp-production-deploy

#B. Pipeline Configuration
Under Pipeline section:

Definition: Pipeline script from SCM

SCM: Git

Repository URL: https://github.com/ogegak2003/myapp.git

Credentials: Select github-credentials

Branch Specifier: */main

Script Path: Jenkinsfile

#C. Additional Requirements
Ensure these Jenkins plugins are installed:

Docker Pipeline

Kubernetes

Slack Notification (optional)

OWASP Dependency-Check (for security scanning)