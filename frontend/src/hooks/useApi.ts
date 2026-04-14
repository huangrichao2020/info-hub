import { useCallback, useEffect, useRef, useState } from 'react'
import client from '../api/client'
import type { AxiosError } from 'axios'

/* ============================================
   useApiFetch - 统一 API 请求 hook
   设计思想：
   - graphify "诚实优于黑盒"：明确区分成功/失败/加载中
   - superpowers "系统化 > 临时发挥"：标准化错误处理流程
   
   使用方式：
   const { data, loading, error, refetch } = useApiFetch('/fin-news', {
     params: { source, hours: 24 },
     deps: [source, refreshKey],  // 依赖变化时自动重新请求
   })
   ============================================ */

interface UseApiFetchOptions {
  /** URL 查询参数 */
  params?: Record<string, unknown>
  /** 依赖数组，变化时自动重新请求 */
  deps?: unknown[]
  /** 是否立即执行（默认 true） */
  immediate?: boolean
  /** 请求超时时间（毫秒） */
  timeout?: number
}

interface UseApiFetchResult<T> {
  data: T | null
  loading: boolean
  error: string | null
  /** 手动触发重新请求 */
  refetch: () => void
  /** 清除错误状态 */
  clearError: () => void
}

export function useApiFetch<T = unknown>(
  url: string,
  options: UseApiFetchOptions = {},
): UseApiFetchResult<T> {
  const { params, deps = [], immediate = true, timeout = 30000 } = options

  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState<string | null>(null)

  const mountedRef = useRef(true)

  const fetchData = useCallback(async () => {
    setError(null)
    if (mountedRef.current) setLoading(true)

    try {
      const response = await client.get<T>(url, { params, timeout })

      if (mountedRef.current) {
        setData(response.data)
      }
    } catch (err) {
      if (!mountedRef.current) return

      const axiosError = err as AxiosError<{ detail?: string }>
      let msg = '请求失败'

      if (axiosError.response) {
        const detail = axiosError.response.data?.detail
        msg = detail || `服务器错误 (${axiosError.response.status})`
      } else if (axiosError.code === 'ECONNABORTED') {
        msg = '请求超时，请稍后重试'
      } else if (axiosError.request) {
        msg = '网络连接失败，请检查后端服务是否启动'
      }

      setError(msg)
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [url, params, timeout])

  const refetch = useCallback(() => {
    void fetchData()
  }, [fetchData])

  const clearError = useCallback(() => setError(null), [])

  // 组件挂载/卸载管理
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  // 依赖变化时自动重新请求
  useEffect(() => {
    if (immediate) {
      void fetchData()
    }
  // biome-ignore lint/correctness/useExhaustiveDependencies: deps 是用户传入的依赖数组
  }, deps)

  return { data, loading, error, refetch, clearError }
}

/* ============================================
   useApiMutation - 统一 POST/PUT/DELETE hook
   用于非幂等操作（生成报告、刷新数据等）
   
   使用方式：
   const { data, loading, error, mutate } = useApiMutation('post', '/review/generate')
   
   // 触发：
   mutate({ ticker: 'AAPL', date: '2024-01-01' })
   ============================================ */

interface UseApiMutationOptions<TData> {
  /** 请求成功回调 */
  onSuccess?: (data: TData) => void
  /** 请求失败回调 */
  onError?: (error: string) => void
}

interface UseApiMutationResult<TVariables, TData> {
  data: TData | null
  loading: boolean
  error: string | null
  /** 发起请求 */
  mutate: (variables: TVariables) => void
  /** 清除错误 */
  clearError: () => void
}

export function useApiMutation<TVariables = Record<string, unknown>, TData = unknown>(
  method: 'post' | 'put' | 'delete',
  url: string,
  options: UseApiMutationOptions<TData> = {},
): UseApiMutationResult<TVariables, TData> {
  const { onSuccess, onError } = options

  const [data, setData] = useState<TData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const mutate = useCallback(
    (variables: TVariables) => {
      setError(null)
      setLoading(true)

      const clientMethod = client[method] as (
        url: string,
        data?: unknown,
      ) => Promise<{ data: TData }>

      clientMethod(url, variables)
        .then((response) => {
          if (mountedRef.current) {
            setData(response.data)
            onSuccess?.(response.data)
          }
        })
        .catch((err) => {
          if (!mountedRef.current) return

          const axiosError = err as AxiosError<{ detail?: string }>
          let msg = '操作失败'

          if (axiosError.response?.data?.detail) {
            msg = axiosError.response.data.detail
          } else if (axiosError.code === 'ECONNABORTED') {
            msg = '请求超时'
          } else if (axiosError.request) {
            msg = '网络连接失败'
          }

          setError(msg)
          onError?.(msg)
        })
        .finally(() => {
          if (mountedRef.current) {
            setLoading(false)
          }
        })
    },
    [method, url, onSuccess, onError],
  )

  const clearError = useCallback(() => setError(null), [])

  return { data, loading, error, mutate, clearError }
}
