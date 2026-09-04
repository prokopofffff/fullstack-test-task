"use client";

import type { ReactNode } from "react";
import { Badge, Card, Spinner } from "react-bootstrap";

type ResourceCardProps = {
  title: string;
  count: number;
  isLoading: boolean;
  isRefreshing?: boolean;
  className?: string;
  children: ReactNode;
};

// Общая обвязка карточки списка: заголовок со спиннером обновления и
// счётчиком, тело со спиннером загрузки либо приглушённой (во время
// рефреша) таблицей. FilesTable и AlertsTable отличаются только
// заголовком, счётчиком и содержимым <Table>.
export function ResourceCard({
  title,
  count,
  isLoading,
  isRefreshing,
  className,
  children,
}: ResourceCardProps) {
  return (
    <Card className={["shadow-sm border-0", className].filter(Boolean).join(" ")}>
      <Card.Header className="bg-white border-0 pt-4 px-4">
        <div className="d-flex justify-content-between align-items-center">
          <h2 className="h5 mb-0 d-flex align-items-center gap-2">
            {title}
            {isRefreshing ? (
              <Spinner
                animation="border"
                size="sm"
                variant="secondary"
                role="status"
                aria-label="Обновление"
              />
            ) : null}
          </h2>
          <Badge bg="secondary">{count}</Badge>
        </div>
      </Card.Header>
      <Card.Body className="px-4 pb-4">
        {isLoading ? (
          <div className="d-flex justify-content-center py-5">
            <Spinner animation="border" />
          </div>
        ) : (
          <div
            className="table-responsive"
            style={isRefreshing ? { opacity: 0.6, transition: "opacity 0.15s" } : undefined}
          >
            {children}
          </div>
        )}
      </Card.Body>
    </Card>
  );
}
