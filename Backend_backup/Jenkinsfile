pipeline {
  agent {
    kubernetes {
      yaml """
  apiVersion: v1
  kind: Pod
  spec:
    serviceAccountName: jenkins
    containers:
    - name: kaniko
      image: gcr.io/kaniko-project/executor:debug
      command:
      - /busybox/sh
      - -c
      - sleep 3600
      tty: true
  """
    }
  }


  environment {
    AWS_ACCOUNT_ID = "416963226971"
    AWS_REGION = "ap-northeast-2"
    ECR_REPO = "bolrea-malrea-backend"
    GIT_USER_NAME = "jenkins-bot"
    GIT_USER_EMAIL = "jenkins@bolrea.dev"
    GITOPS_REPO_URL = "github.com/SpringDaylight/Bolrea-Malrea-Gitops.git"
  }

  stages {

    stage("Set Build Context") {
      steps {
        script {
          if (env.BRANCH_NAME == "develop") {
            env.ENV_NAME = "dev"
            env.IMAGE_TAG = "dev-${env.GIT_COMMIT.take(7)}"
            env.GITOPS_PATH = "overlays/dev/backend"
          } else if (env.BRANCH_NAME == "main") {
            env.ENV_NAME = "prod"
            env.IMAGE_TAG = "prod-${env.GIT_COMMIT.take(7)}"
            env.GITOPS_PATH = "overlays/prod/backend"
          } else {
            error("Unsupported branch: ${env.BRANCH_NAME}")
          }
          echo "ENV_NAME=${env.ENV_NAME}"
          echo "IMAGE_TAG=${env.IMAGE_TAG}"
        }
      }
    }

    stage("Build & Push Image") {
      steps {
        container("kaniko") {
          sh """
            /kaniko/executor \
              --dockerfile=Dockerfile \
              --context=. \
              --destination=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG} \
              --verbosity=info
          """
        }
      }
    }

    stage("Update GitOps Repo") {
      steps {
        withCredentials([string(credentialsId: 'github-token', variable: 'GITHUB_TOKEN')]) {
          sh """
            rm -rf gitops
            git clone https://${GITHUB_TOKEN}@${GITOPS_REPO_URL} gitops
            cd gitops

            git config user.name "${GIT_USER_NAME}"
            git config user.email "${GIT_USER_EMAIL}"

            sed -i 's|image: .*|image: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}|' \
              ${GITOPS_PATH}/patch-deployment.yaml

            git add ${GITOPS_PATH}/patch-deployment.yaml

            # 변경 없으면 commit 실패 방지
            git diff --cached --quiet || \
              git commit -m "ci(${ENV_NAME}): update backend image to ${IMAGE_TAG}"

            git push origin main
          """
        }
      }
    }
  }
}
