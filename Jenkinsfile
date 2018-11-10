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
                sh 'scp -r . tidylobster@95.216.149.46:/home/tidylobster/substitute-bot/'
                sh 'screen -S subsitute-bot -X quit'
                sh 'screen -dmS substitute-bot bash -c "python3 /home/tidylobster/substitute-bot/bot.py"'
            }
        }
    }
}