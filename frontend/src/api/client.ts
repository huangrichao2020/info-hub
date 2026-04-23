import axios from 'axios'

const client = axios.create({
  baseURL: '/info-hub/api',
  timeout: 30000,
})

export default client
