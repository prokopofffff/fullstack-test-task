"use client";

import { Badge, Button, Table } from "react-bootstrap";
import { processingVariant, type FileItem } from "@/entities/file/model";
import { formatDate, formatSize } from "@/shared/lib/format";
import { ResourceCard } from "@/shared/ui/ResourceCard";

type FilesTableProps = {
  files: FileItem[];
  isLoading: boolean;
  isRefreshing?: boolean;
  downloadUrl: (id: string) => string;
};

export function FilesTable({ files, isLoading, isRefreshing, downloadUrl }: FilesTableProps) {
  return (
    <ResourceCard
      title="Файлы"
      count={files.length}
      isLoading={isLoading}
      isRefreshing={isRefreshing}
      className="mb-4"
    >
      <Table hover bordered className="align-middle mb-0">
        <thead className="table-light">
          <tr>
            <th>Название</th>
            <th>Файл</th>
            <th>MIME</th>
            <th>Размер</th>
            <th>Статус</th>
            <th>Проверка</th>
            <th>Создан</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {files.length === 0 ? (
            <tr>
              <td colSpan={8} className="text-center py-4 text-secondary">
                Файлы пока не загружены
              </td>
            </tr>
          ) : (
            files.map((file) => (
              <tr key={file.id}>
                <td>
                  <div className="fw-semibold">{file.title}</div>
                  <div className="small text-secondary">{file.id}</div>
                </td>
                <td>{file.original_name}</td>
                <td>{file.mime_type}</td>
                <td>{formatSize(file.size)}</td>
                <td>
                  <Badge bg={processingVariant(file.processing_status)}>
                    {file.processing_status}
                  </Badge>
                </td>
                <td>
                  <div className="d-flex flex-column gap-1">
                    <Badge bg={file.requires_attention ? "warning" : "success"}>
                      {file.scan_status ?? "pending"}
                    </Badge>
                    <span className="small text-secondary">
                      {file.scan_details ?? "Ожидает обработки"}
                    </span>
                  </div>
                </td>
                <td>{formatDate(file.created_at)}</td>
                <td className="text-nowrap">
                  <Button as="a" href={downloadUrl(file.id)} variant="outline-primary" size="sm">
                    Скачать
                  </Button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </Table>
    </ResourceCard>
  );
}
