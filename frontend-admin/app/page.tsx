import Link from "next/link"

export default function Home() {
  return (
    <main className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Vancelian Admin</h1>
      <p className="text-gray-600 mb-8">Admin frontend is running</p>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          href="/users"
          className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <h2 className="text-xl font-semibold mb-2">Users</h2>
          <p className="text-gray-600 text-sm">View and manage all users</p>
        </Link>
        
        <Link
          href="/compliance"
          className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <h2 className="text-xl font-semibold mb-2">Compliance</h2>
          <p className="text-gray-600 text-sm">Review deposits and compliance status</p>
        </Link>
        
        <Link
          href="/tools/zand-webhook"
          className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <h2 className="text-xl font-semibold mb-2">ZAND Webhook</h2>
          <p className="text-gray-600 text-sm">Simulate ZAND bank webhooks</p>
        </Link>
      </div>
    </main>
  )
}

