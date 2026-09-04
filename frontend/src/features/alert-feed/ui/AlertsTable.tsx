"use client";

import { Badge, Table } from "react-bootstrap";
import { levelVariant, type AlertItem } from "@/entities/alert/model";
import { formatDate } from "@/shared/lib/format";
import { ResourceCard } from "@/shared/ui/ResourceCard";

type AlertsTableProps = {
  alerts: AlertItem[];
  isLoading: boolean;
  isRefreshing?: boolean;
};

export function AlertsTable({ alerts, isLoading, isRefreshing }: AlertsTableProps) {
  return (
    <ResourceCard title="Алерты" count={alerts.length} isLoading={isLoading} isRefreshing={isRefreshing}>
      <Table hover bordered className="align-middle mb-0">
        <thead className="table-light">
          <tr>
            <th>ID</th>
            <th>File ID</th>
            <th>Уровень</th>
            <th>Сообщение</th>
            <th>Создан</th>
          </tr>
        </thead>
        <tbody>
          {alerts.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-center py-4 text-secondary">
                Алертов пока нет
              </td>
            </tr>
          ) : (
            alerts.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td className="small">{item.file_id}</td>
                <td>
                  <Badge bg={levelVariant(item.level)}>{item.level}</Badge>
                </td>
                <td>{item.message}</td>
                <td>{formatDate(item.created_at)}</td>
              </tr>
            ))
          )}
        </tbody>
      </Table>
    </ResourceCard>
  );
}
