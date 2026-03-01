output "queue_id" {
  value = google_cloud_tasks_queue.process_entry_ai.id
}

output "queue_name" {
  value = google_cloud_tasks_queue.process_entry_ai.name
}
