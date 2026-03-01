locals {
  name_prefix = "${var.app_prefix}-${var.env}"
  common_labels = merge(
    {
      app = var.app_prefix
      env = var.env
    },
    var.labels
  )
}

# Platform foundation
module "project_services" {
  source = "./modules/project_services"

  project_id = var.project_id

  services = [
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudtasks.googleapis.com",
    "firebase.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "run.googleapis.com"
  ]
}

module "iam" {
  source = "./modules/iam"

  project_id       = var.project_id
  app_prefix       = var.app_prefix
  env              = var.env
  labels           = local.common_labels
  depends_on_apis  = module.project_services.enabled_services

  depends_on = [module.project_services]
}

module "firestore" {
  source = "./modules/firestore"

  project_id = var.project_id
  location   = var.firestore_location
  depends_on_apis = module.project_services.enabled_services

  depends_on = [module.project_services]
}

module "workflow_primitives" {
  source = "./modules/workflow_primitives"

  project_id                        = var.project_id
  region                            = var.queue_region
  app_prefix                        = var.app_prefix
  env                               = var.env
  max_dispatches_per_second         = var.queue_max_dispatches_per_second
  max_concurrent_dispatches         = var.queue_max_concurrent_dispatches
  depends_on_apis                   = module.project_services.enabled_services

  depends_on = [module.project_services]
}

module "observability" {
  source = "./modules/observability"

  project_id  = var.project_id
  app_prefix  = var.app_prefix
  env         = var.env

  depends_on = [module.project_services]
}
