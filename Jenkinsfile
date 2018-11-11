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
                sh 'python3 -m py_compile $(find . -type f -name "*.py")'
            }
            post {
                failure {
                    telegramSend 'Build for @substitute\\_bot has been failed'
                }
            }
        }
        stage('Test') {
            steps {
                sh 'ssh root@95.216.149.46 rm -rf /root/tests/substitute-bot/*'  // clean up directory
                sh 'scp -r ./* root@95.216.149.46:/root/tests/substitute-bot/'  // copy all compiled files 
                sh 'ssh root@95.216.149.46 cp test_account.session config.env substitute-bot/'  // copy session files
                sh 'ssh root@95.216.149.46 make test -C /root/tests/substitute-bot/' // create new bot instance and run tests
            }
            post {
                success {
                    telegramSend 'All tests for @substitute\\_bot have been passed'
                }
                failure {
                    telegramSend 'Tests for @substitute\\_bot have been failed'
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