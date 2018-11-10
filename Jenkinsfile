pipeline {
    agent any
    stages {
        stage('Build') {
            agent {
                docker {
                    image 'python:3.6.7-alpine3.7'
                }
            }
            steps {
                sh 'python3 -m py_compile $(ls ./**/*.py)'
            }
            post {
                failure {
                    telegramSend 'Build for @substitute\\_bot has been failed'
                }
            }
        }
        stage('Deploy') {
            steps {
                sh 'scp -r ./* root@95.216.149.46:/root/substitute-bot/'
                sh 'ssh root@95.216.149.46 make deploy -C /root/substitute-bot/'
            }
            post {
                success {
                    telegramSend '@substitute\\_bot has been successfully updated'
                }
                failure {
                    telegramSend 'Deploy for @substitute\\_bot has been failed'
                }
            }
        }
    }
}