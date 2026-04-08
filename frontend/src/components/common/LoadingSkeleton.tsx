export default function LoadingSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
      gap: 14,
    }}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            background: 'var(--color-card)',
            border: '1px solid var(--color-border)',
            borderRadius: 12,
            padding: '14px 16px',
          }}
        >
          <div style={{ height: 12, background: 'var(--color-border)', borderRadius: 6, width: '40%', marginBottom: 12 }} />
          <div style={{ height: 14, background: 'var(--color-border)', borderRadius: 6, width: '90%', marginBottom: 8 }} />
          <div style={{ height: 12, background: 'var(--color-border)', borderRadius: 6, width: '70%', marginBottom: 12 }} />
          <div style={{ display: 'flex', gap: 6 }}>
            <div style={{ height: 18, width: 50, background: 'var(--color-border)', borderRadius: 999 }} />
            <div style={{ height: 18, width: 60, background: 'var(--color-border)', borderRadius: 999 }} />
          </div>
        </div>
      ))}
    </div>
  )
}
