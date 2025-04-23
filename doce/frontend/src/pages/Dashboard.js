import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title } from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';
import { DocumentTextIcon, DocumentDuplicateIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

// Register ChartJS components
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title);

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    invoiceCount: 0,
    contractCount: 0,
    invoicesByStatus: {
      Received: 0,
      Processing: 0,
      OCRd: 0,
      Validated: 0,
      Flagged: 0,
      'Pending Review': 0,
      'Pending Approval': 0,
      Approved: 0,
      Rejected: 0,
      Error: 0
    },
    recentInvoices: []
  });

  useEffect(() => {
    // In a real application, we would fetch this data from the API
    // For now, we'll use mock data
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Mock data for demonstration
        const mockStats = {
          invoiceCount: 156,
          contractCount: 42,
          invoicesByStatus: {
            Received: 5,
            Processing: 3,
            OCRd: 8,
            Validated: 25,
            Flagged: 15,
            'Pending Review': 12,
            'Pending Approval': 18,
            Approved: 62,
            Rejected: 5,
            Error: 3
          },
          recentInvoices: [
            { id: 1, vendor_name: 'Acme Corp', invoice_number: 'INV-001', total_amount: 1250.00, status: 'Approved', upload_timestamp: '2023-10-15T14:30:00Z' },
            { id: 2, vendor_name: 'Globex Inc', invoice_number: 'INV-2023-42', total_amount: 3750.50, status: 'Flagged', upload_timestamp: '2023-10-14T09:15:00Z' },
            { id: 3, vendor_name: 'Initech', invoice_number: 'IN-789456', total_amount: 950.25, status: 'Pending Approval', upload_timestamp: '2023-10-13T16:45:00Z' },
            { id: 4, vendor_name: 'Umbrella Corp', invoice_number: 'UMB-2023-10-123', total_amount: 5280.75, status: 'Validated', upload_timestamp: '2023-10-12T11:20:00Z' },
            { id: 5, vendor_name: 'Wayne Enterprises', invoice_number: 'WE-10152023', total_amount: 12750.00, status: 'Pending Review', upload_timestamp: '2023-10-11T13:10:00Z' }
          ]
        };
        
        setStats(mockStats);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data');
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Prepare chart data for invoice status
  const statusChartData = {
    labels: Object.keys(stats.invoicesByStatus),
    datasets: [
      {
        data: Object.values(stats.invoicesByStatus),
        backgroundColor: [
          '#0ea5e9', // Received - primary-500
          '#38bdf8', // Processing - primary-400
          '#7dd3fc', // OCRd - primary-300
          '#22c55e', // Validated - green-500
          '#f59e0b', // Flagged - amber-500
          '#64748b', // Pending Review - secondary-500
          '#6366f1', // Pending Approval - indigo-500
          '#10b981', // Approved - emerald-500
          '#ef4444', // Rejected - red-500
          '#94a3b8', // Error - secondary-400
        ],
        borderWidth: 1,
      },
    ],
  };

  // Format date for display
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }).format(date);
  };

  // Status badge component
  const StatusBadge = ({ status }) => {
    let color;
    let icon;
    
    switch (status) {
      case 'Approved':
        color = 'bg-green-100 text-green-800';
        icon = <CheckCircleIcon className="w-4 h-4 mr-1" />;
        break;
      case 'Flagged':
        color = 'bg-amber-100 text-amber-800';
        icon = <ExclamationTriangleIcon className="w-4 h-4 mr-1" />;
        break;
      case 'Rejected':
        color = 'bg-red-100 text-red-800';
        icon = <ExclamationTriangleIcon className="w-4 h-4 mr-1" />;
        break;
      case 'Validated':
        color = 'bg-green-100 text-green-800';
        icon = <CheckCircleIcon className="w-4 h-4 mr-1" />;
        break;
      case 'Pending Review':
      case 'Pending Approval':
        color = 'bg-blue-100 text-blue-800';
        icon = <DocumentTextIcon className="w-4 h-4 mr-1" />;
        break;
      default:
        color = 'bg-gray-100 text-gray-800';
        icon = <DocumentTextIcon className="w-4 h-4 mr-1" />;
    }
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
        {icon}
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg font-medium text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 mt-4 text-red-700 bg-red-100 rounded-md">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="pb-5 border-b border-gray-200">
        <h1 className="text-2xl font-bold leading-6 text-gray-900">Dashboard</h1>
      </div>
      
      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-5 mt-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="overflow-hidden bg-white rounded-lg shadow">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 p-3 bg-primary-100 rounded-md">
                <DocumentTextIcon className="w-6 h-6 text-primary-600" aria-hidden="true" />
              </div>
              <div className="flex-1 w-0 ml-5">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Invoices</dt>
                  <dd className="text-3xl font-semibold text-gray-900">{stats.invoiceCount}</dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="px-5 py-3 bg-gray-50">
            <div className="text-sm">
              <Link to="/invoices" className="font-medium text-primary-600 hover:text-primary-900">
                View all
              </Link>
            </div>
          </div>
        </div>

        <div className="overflow-hidden bg-white rounded-lg shadow">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 p-3 bg-primary-100 rounded-md">
                <DocumentDuplicateIcon className="w-6 h-6 text-primary-600" aria-hidden="true" />
              </div>
              <div className="flex-1 w-0 ml-5">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Contracts</dt>
                  <dd className="text-3xl font-semibold text-gray-900">{stats.contractCount}</dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="px-5 py-3 bg-gray-50">
            <div className="text-sm">
              <Link to="/contracts" className="font-medium text-primary-600 hover:text-primary-900">
                View all
              </Link>
            </div>
          </div>
        </div>

        <div className="overflow-hidden bg-white rounded-lg shadow sm:col-span-2">
          <div className="p-5">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Invoice Status</h3>
            <div className="mt-2 h-60">
              <Pie data={statusChartData} options={{ maintainAspectRatio: false }} />
            </div>
          </div>
        </div>
      </div>

      {/* Recent invoices */}
      <div className="mt-8">
        <div className="pb-5 border-b border-gray-200">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Recent Invoices</h2>
        </div>
        <div className="mt-4 overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
          <table className="min-w-full divide-y divide-gray-300">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Vendor</th>
                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Invoice #</th>
                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Amount</th>
                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Date</th>
                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Status</th>
                <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                  <span className="sr-only">View</span>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {stats.recentInvoices.map((invoice) => (
                <tr key={invoice.id}>
                  <td className="py-4 pl-4 pr-3 text-sm font-medium text-gray-900 whitespace-nowrap sm:pl-6">
                    {invoice.vendor_name}
                  </td>
                  <td className="px-3 py-4 text-sm text-gray-500 whitespace-nowrap">{invoice.invoice_number}</td>
                  <td className="px-3 py-4 text-sm text-gray-500 whitespace-nowrap">
                    ${invoice.total_amount.toFixed(2)}
                  </td>
                  <td className="px-3 py-4 text-sm text-gray-500 whitespace-nowrap">
                    {formatDate(invoice.upload_timestamp)}
                  </td>
                  <td className="px-3 py-4 text-sm text-gray-500 whitespace-nowrap">
                    <StatusBadge status={invoice.status} />
                  </td>
                  <td className="relative py-4 pl-3 pr-4 text-sm font-medium text-right whitespace-nowrap sm:pr-6">
                    <Link to={`/invoices/${invoice.id}`} className="text-primary-600 hover:text-primary-900">
                      View<span className="sr-only">, {invoice.invoice_number}</span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 text-right">
          <Link to="/invoices" className="text-sm font-medium text-primary-600 hover:text-primary-900">
            View all invoices →
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;