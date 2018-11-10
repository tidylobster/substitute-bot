pipeline {
    agent any
    stages {
        stage('Clean') {
            steps {
                sh 'pwd'
                sh 'ls'
            }
        }
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
    }
}