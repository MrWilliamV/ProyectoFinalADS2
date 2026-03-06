
// ================================
// ENTORNOS DEFINIDOS
// ================================


def runFarmaciaPlaybook(String tagName) {
    def TARGETS = [
      test: [
        ip:      'lenovo-server-ip',
        ssh:     'ssh-william-lenovo-server',
        env:     'farmacia-django-env-test',
        compose: 'django-farmacia-docker-compose'
      ],
      contabo: [
        ip:      'vps-contabo-ip',
        ssh:     'ssh-william-contabo-vps',
        env:     'farmacia-django-env-test',
        compose: 'django-farmacia-docker-compose'
      ]

    ]

  def cfg = TARGETS[params.TARGET]

  if (!cfg) {
    error "TARGET inválido: ${params.TARGET}"
  }

  withCredentials([
    string(credentialsId: cfg.ip, variable: 'SERVER_IP'),
    file(credentialsId: cfg.env, variable: 'ENV_FILE'),
    file(credentialsId: cfg.compose, variable: 'DOCKER_COMPOSE_FILE')
  ]) {

    env.SERVER_IP = SERVER_IP

    ansiblePlaybook(
      playbook: 'ci/playbook.yml',
      inventory: "${SERVER_IP},",
      credentialsId: cfg.ssh,
      extras: "--tags ${tagName}",
      extraVars: [
          env_file: "${WORKSPACE}/.env",
          compose_file: DOCKER_COMPOSE_FILE,
          ansible_host: SERVER_IP,
          compose_project_name: env.COMPOSE_PROJECT_NAME
       ]
    )
  }
}

// ================================
// PIPELINE
// ================================
pipeline {
  agent any

  parameters {
    choice(name: 'TARGET', choices: ['test', 'contabo'], description: 'Ambiente destino')
    string(name: 'TRACKING_ID', defaultValue: '', description: 'ID de seguimiento (uuid)')
    string(name: 'COMPOSE_PROJECT_NAME', defaultValue: 'farmacia-django', description: 'Nombre de la farmacia')
    string(name: 'DJANGO_SUPERUSER_USERNAME', defaultValue: 'admin', description: 'Cliente admin username')
    string(name: 'DJANGO_SUPERUSER_EMAIL', defaultValue: 'admin@gmail.com', description: 'Cliente admin email')
    password(name: 'DJANGO_SUPERUSER_PASSWORD', defaultValue: '', description: 'Cliente password')
    string(name: 'NGINX_PORT', defaultValue: '8000', description: 'Puerto externo para Nginx')
    string(name: 'MYSQL_PUBLISHED_PORT', defaultValue: '3307', description: 'Puerto externo para MySQL')
  }

  tools {
    git 'Default'
  }

  environment {
    ANSIBLE_CONFIG = "${WORKSPACE}/ci/ansible.cfg"
    FLASK_WEBHOOK_BASE = "http://flask_orquestador:5000"
  }

  stages {

  stage('Notify Started') {
      steps {
        script {
          def payload = """{
            "event":"STARTED",
            "job":"${env.JOB_NAME}",
            "build":"${env.BUILD_NUMBER}",
            "target":"${params.TARGET}",
            "url":"${env.BUILD_URL}",
            "message":"Build iniciado"
          }"""

          def hookUrl = params.TRACKING_ID?.trim()
            ? "${env.FLASK_WEBHOOK_BASE}/jenkins/webhook/${params.TRACKING_ID}"
            : "${env.FLASK_WEBHOOK_BASE}/jenkins/webhook"

          sh """
            curl -s -X POST -H 'Content-Type: application/json' \
            -d '${payload}' \
            '${hookUrl}' || true
          """
        }
      }
    }

  stage('Build .env for instance') {
      steps {
        script {
          if (!params.TRACKING_ID?.trim()) { error "TRACKING_ID es obligatorio" }

          def baseName = params.COMPOSE_PROJECT_NAME?.trim()
          if (!baseName) { error "COMPOSE_PROJECT_NAME requerido" }

          env.COMPOSE_PROJECT_NAME = "${baseName}_${params.TRACKING_ID.trim()}".replaceAll('[^a-zA-Z0-9_-]','_')

          env.GEN_SECRET_KEY = sh(
              script: "python -c \"import secrets; print(secrets.token_urlsafe(50))\"",
              returnStdout: true
          ).trim()

          writeFile file: '.env', text: """
            DJANGO_SUPERUSER_USERNAME=${params.DJANGO_SUPERUSER_USERNAME}
            DJANGO_SUPERUSER_EMAIL=${params.DJANGO_SUPERUSER_EMAIL}
            DJANGO_SUPERUSER_PASSWORD=${params.DJANGO_SUPERUSER_PASSWORD}
            SECRET_KEY=${env.GEN_SECRET_KEY}
            ALLOWED_HOSTS=*

            DEBUG=True
            MYSQL_DATABASE=farmacia
            MYSQL_USER=william
            MYSQL_PASSWORD=1234
            MYSQL_HOST=mysql
            MYSQL_PORT=3306
            MYSQL_ROOT_PASSWORD=root

            CSRF_TRUSTED_ORIGINS=http://${env.SERVER_IP}:${params.NGINX_PORT}

            MYSQL_PUBLISHED_PORT=${params.MYSQL_PUBLISHED_PORT}
            NGINX_PORT=${params.NGINX_PORT}
            COMPOSE_PROJECT_NAME=${env.COMPOSE_PROJECT_NAME}
            FLASK_WEBHOOK_BASE=http://flask_orquestador:5000
    """.trim() + "\n"
        }
      }
    }

    stage('Desplegando') {
      steps { script { runFarmaciaPlaybook('deploy') } }
    }

    stage('Ejecutando tests') {
        steps {
            script {
                runFarmaciaPlaybook('test')
            }
        }
    }

    stage('Migraciones') {
      steps { script { runFarmaciaPlaybook('migrate') } }
    }

    stage('Crear superusuario') {
      steps { script { runFarmaciaPlaybook('superuser') } }
    }

    stage('Asignar rol') {
      steps { script { runFarmaciaPlaybook('role') } }
    }

  }

    post {
      always {
        script {
          def payload = """{
            "event":"FINISHED",
            "job":"${env.JOB_NAME}",
            "build":"${env.BUILD_NUMBER}",
            "result":"${currentBuild.currentResult}",
            "target":"${params.TARGET}",
            "url":"${env.BUILD_URL}",
            "message":"Finalizó con estado: ${currentBuild.currentResult}"
          }"""

          def hookUrl = params.TRACKING_ID?.trim()
            ? "${env.FLASK_WEBHOOK_BASE}/jenkins/webhook/${params.TRACKING_ID}"
            : "${env.FLASK_WEBHOOK_BASE}/jenkins/webhook"

          echo "Webhook URL: ${hookUrl}"

          sh """
            curl -s -X POST -H 'Content-Type: application/json' \
            -d '${payload}' \
            '${hookUrl}' || true
          """
        }
      }

      success { echo "¡Despliegue exitoso!" }
      failure { echo "xxxxx El Pipeline falló. xxxxx" }
    }
}
