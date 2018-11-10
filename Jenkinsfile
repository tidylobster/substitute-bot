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
                sh 'python3 -m py_compile bot.py $(ls ./**/*.py)'
            }
        }
        stage('Deploy') {
            steps {
                sh 'scp -r ./* root@95.216.149.46:/root/substitute-bot/'
                sh 'ssh root@95.216.149.46 cd /root/substitute-bot/; make deploy'
            }
        }
    }
}