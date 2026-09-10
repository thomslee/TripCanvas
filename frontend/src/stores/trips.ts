import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tripsApi, type Trip } from '../api'

export const useTripsStore = defineStore('trips', () => {
  const trips = ref<Trip[]>([])
  const loading = ref(false)

  async function fetchTrips() {
    loading.value = true
    try {
      const { data } = await tripsApi.list()
      trips.value = data
    } finally {
      loading.value = false
    }
  }

  async function removeTrip(id: number) {
    await tripsApi.remove(id)
    trips.value = trips.value.filter((t) => t.id !== id)
  }

  return { trips, loading, fetchTrips, removeTrip }
})
