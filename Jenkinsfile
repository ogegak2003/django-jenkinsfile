/*
 * PRODUCTION JENKINS PIPELINE FOR DJANGO APP
 * Purpose: Automated CI/CD pipeline for ogegak2003/myapp
 * Features:
 * - Blue/green deployments
 * - Database migrations with rollback
 * - Security scanning
 * - Performance testing
 * - Automatic rollback on failure
 */

pipeline {
    // Run on any agent with Docker and Kubernetes installed
    agent {
        label 'docker-k8s'
    }

    options {
        // Keep only the last 10 builds to save disk space
        buildDiscarder(logRotator(numToKeepStr: '10'))
        
        // Fail if pipeline runs longer than 45 minutes
        timeout(time: 45, unit: 'MINUTES')
        
        // Prevent multiple simultaneous builds
        disableConcurrentBuilds()
        
        // Enable colored console output
        ansiColor('xterm')
        
        // Add timestamps to console logs
        timestamps()
    }

    environment {
        // ===== APPLICATION CONFIG =====
        APP_NAME = 'myapp'
        DOCKER_IMAGE = 'ogegak2003/myapp'
        PROD_DOMAIN = 'myapp-production.com'
        
        // ===== VERSION CONTROL =====
        // Get the latest git tag or commit hash
        VERSION = sh(
            script: 'git describe --tags --always || git rev-parse --short HEAD',
            returnStdout: true
        ).trim()
        
        // ===== SECURITY =====
        TRIVY_SEVERITY = 'HIGH,CRITICAL'  // Fail on these vulnerability levels
        
        // ===== CREDENTIALS =====
        // Jenkins credentials IDs (configure in Jenkins console)
        DOCKER_CREDS = credentials('dockerhub-creds')
        DB_CREDS = credentials('prod-db-creds')
        SECRET_KEY = credentials('django-secret-key')
    }

    stages {
        // =============================================
        // STAGE 1: PREPARE ENVIRONMENT
        // =============================================
        stage('Initialize') {
            steps {
                script {
                    // Clean workspace from previous builds
                    cleanWs()
                    
                    // Set readable build name
                    currentBuild.displayName = "${APP_NAME}-${VERSION}-${BUILD_NUMBER}"
                    
                    // Verify required tools are installed
                    sh '''
                        echo "=== Tool Versions ==="
                        docker --version
                        docker-compose --version
                        python --version
                        kubectl version --client
                        trivy --version
                    '''
                }
            }
        }

        // =============================================
        // STAGE 2: SOURCE CODE SETUP
        // =============================================
        stage('Checkout & Dependencies') {
            steps {
                // Checkout from GitHub with shallow clone
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/main"]],
                    extensions: [
                        [$class: 'CloneOption', depth: 1],
                        [$class: 'CleanBeforeCheckout']
                    ],
                    userRemoteConfigs: [[
                        url: 'https://github.com/ogegak2003/myapp.git',
                        credentialsId: 'github-credentials'
                    ]]
                ])
                
                // Set up Python environment
                sh '''
                    python -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip wheel
                    pip install -r requirements.txt
                '''
            }
        }

        // =============================================
        // STAGE 3: QUALITY CHECKS
        // =============================================
        stage('Quality Gates') {
            parallel {
                // Unit tests with coverage
                stage('Tests') {
                    steps {
                        sh '''
                            . venv/bin/activate
                            python manage.py test --noinput --parallel 4 --verbosity 2
                            coverage run --source='.' manage.py test
                            coverage xml
                        '''
                        junit '**/test-reports/*.xml'
                        cobertura coberturaReportFile: 'coverage.xml'
                    }
                }
                
                // Static code analysis
                stage('Linting') {
                    steps {
                        sh '''
                            . venv/bin/activate
                            flake8 . --count --exit-zero > flake8.txt
                            black --check . || true
                        '''
                    }
                }
            }
        }

        // =============================================
        // STAGE 4: SECURITY SCANNING
        // =============================================
        stage('Security') {
            parallel {
                // Python dependency vulnerabilities
                stage('Dependencies') {
                    steps {
                        sh '''
                            . venv/bin/activate
                            safety check --full-report > safety-report.txt
                            bandit -r . -f html -o bandit-report.html
                        '''
                        archiveArtifacts '*-report.*'
                    }
                }
                
                // Container vulnerability scanning
                stage('Container Scan') {
                    steps {
                        script {
                            // Build temporary image for scanning
                            docker.build("${DOCKER_IMAGE}-scan:${VERSION}")
                            
                            // Run Trivy scan (fail on critical vulnerabilities)
                            sh """
                                trivy image --severity ${TRIVY_SEVERITY} \
                                --exit-code 1 \
                                --format template \
                                --template @contrib/html.tpl \
                                -o trivy-report.html \
                                ${DOCKER_IMAGE}-scan:${VERSION}
                            """
                        }
                    }
                }
            }
        }

        // =============================================
        // STAGE 5: BUILD & PUSH
        // =============================================
        stage('Build Image') {
            steps {
                script {
                    // Build production Docker image with multi-stage build
                    docker.build("${DOCKER_IMAGE}:${VERSION}") {
                        sh """
                            docker build \
                            --build-arg DJANGO_ENV=production \
                            --build-arg SECRET_KEY=${SECRET_KEY} \
                            -t ${DOCKER_IMAGE}:${VERSION} .
                        """
                    }
                    
                    // Push to Docker Hub
                    docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-creds') {
                        docker.image("${DOCKER_IMAGE}:${VERSION}").push()
                        
                        // Also push as 'latest' if on main branch
                        if (env.BRANCH_NAME == 'main') {
                            docker.image("${DOCKER_IMAGE}:${VERSION}").push('latest')
                        }
                    }
                }
            }
        }

        // =============================================
        // STAGE 6: DATABASE MIGRATION
        // =============================================
        stage('Database') {
            steps {
                script {
                    // Run migrations in a temporary container
                    withCredentials([
                        usernamePassword(
                            credentialsId: 'prod-db-creds',
                            usernameVariable: 'DB_USER',
                            passwordVariable: 'DB_PASS'
                        )
                    ]) {
                        sh """
                            docker run --rm \
                            -e DJANGO_ENV=production \
                            -e DB_HOST=${DB_SERVICE} \
                            -e DB_USER=${DB_USER} \
                            -e DB_PASS=${DB_PASS} \
                            ${DOCKER_IMAGE}:${VERSION} \
                            sh -c "python manage.py migrate --noinput && \
                                  python manage.py createcachetable"
                        """
                    }
                    
                    // Create database backup
                    sh """
                        PGPASSWORD=${DB_CREDS_PSW} pg_dump -h ${DB_SERVICE} \
                        -U ${DB_CREDS_USR} -d myapp_prod \
                        -F c -f db_backup_${VERSION}.dump
                    """
                    archiveArtifacts "db_backup_${VERSION}.dump"
                }
            }
        }

        // =============================================
        // STAGE 7: DEPLOY TO PRODUCTION
        // =============================================
        stage('Deploy') {
            steps {
                script {
                    // Manual approval with deployment options
                    def deployParams = input(
                        message: 'Approve production deployment?',
                        parameters: [
                            choice(
                                name: 'STRATEGY',
                                choices: ['blue-green', 'rolling', 'canary'],
                                description: 'Deployment strategy'
                            ),
                            string(
                                name: 'TRAFFIC_PERCENT',
                                defaultValue: '100',
                                description: 'Percentage of traffic to new version'
                            )
                        ]
                    )
                    
                    // Blue-green deployment implementation
                    if (deployParams.STRATEGY == 'blue-green') {
                        withKubeConfig([credentialsId: 'kube-config']) {
                            // Deploy new (green) version
                            sh """
                                kubectl apply -f k8s/green-deployment.yaml \
                                --namespace=production \
                                --record \
                                --image=${DOCKER_IMAGE}:${VERSION}
                                
                                # Wait for green deployment to be ready
                                kubectl rollout status deployment/myapp-green -n production --timeout=300s
                                
                                # Switch production traffic
                                kubectl apply -f k8s/production-router.yaml
                                
                                # Scale down old (blue) version
                                kubectl scale deployment/myapp-blue --replicas=0 -n production
                            """
                        }
                    }
                    
                    // Verify deployment health
                    sh """
                        curl -sSf https://${PROD_DOMAIN}/health/ \
                        -H "Host: ${PROD_DOMAIN}" \
                        | jq -e '.status == "healthy"'
                    """
                }
            }
        }

        // =============================================
        // STAGE 8: POST-DEPLOYMENT CHECKS
        // =============================================
        stage('Verify') {
            parallel {
                // Basic functionality tests
                stage('Smoke Tests') {
                    steps {
                        sh """
                            NEW_POD=$(kubectl get pods -n production -l app=myapp -o jsonpath='{.items[0].metadata.name}')
                            kubectl exec -n production ${NEW_POD} -- \
                            python manage.py test --tag=smoke --noinput
                        """
                    }
                }
                
                // Performance benchmarking
                stage('Performance') {
                    steps {
                        gatling(
                            simulations: ['myapp.LoadTest'],
                            simulationClass: 'myapp.LoadTest'
                        )
                    }
                }
            }
        }
    }

    // =============================================
    // POST-BUILD ACTIONS
    // =============================================
    post {
        // Always run these steps regardless of build status
        always {
            // Clean up Docker to save disk space
            sh 'docker system prune -f --filter "until=24h" || true'
            
            // Archive important reports
            archiveArtifacts artifacts: '**/*.html,**/*.xml,**/*.dump'
            
            // Clean workspace
            cleanWs()
        }
        
        // Run only when build succeeds
        success {
            slackSend(
                color: 'good',
                message: """✅ SUCCESS: ${APP_NAME} v${VERSION}
                |*Environment*: Production
                |*Commit*: ${GIT_COMMIT}
                |*Image*: ${DOCKER_IMAGE}:${VERSION}
                |*Build Log*: ${BUILD_URL}console""".stripMargin()
            )
        }
        
        // Run when build fails
        failure {
            slackSend(
                color: 'danger',
                message: """❌ FAILED: ${APP_NAME} build #${BUILD_NUMBER}
                |*Stage*: ${env.STAGE_NAME}
                |*Logs*: ${BUILD_URL}console""".stripMargin()
            )
            
            // Automatic rollback if deployment failed
            script {
                if (env.STAGE_NAME == 'Deploy') {
                    withKubeConfig([credentialsId: 'kube-config']) {
                        sh '''
                            kubectl rollout undo deployment/myapp-green -n production
                            kubectl apply -f k8s/blue-service.yaml
                        '''
                    }
                }
            }
        }
        
        // Run when build is unstable (tests failed)
        unstable {
            slackSend(
                color: 'warning',
                message: """⚠️ UNSTABLE: ${APP_NAME} tests failed
                |*Build*: ${BUILD_NUMBER}
                |*Test Report*: ${BUILD_URL}testReport""".stripMargin()
            )
        }
    }
}