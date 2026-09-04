"use client";

import { useState } from "react";
import { Alert, Button, Card, Col, Container, Row } from "react-bootstrap";

import { useFiles } from "@/features/file-list/model/useFiles";
import { FilesTable } from "@/features/file-list/ui/FilesTable";
import { downloadUrl } from "@/features/file-list/api/filesApi";
import { hasPending } from "@/entities/file/model";

import { useAlerts } from "@/features/alert-feed/model/useAlerts";
import { AlertsTable } from "@/features/alert-feed/ui/AlertsTable";

import { useUploadFile } from "@/features/file-upload/model/useUploadFile";
import { UploadFileModal } from "@/features/file-upload/ui/UploadFileModal";

export default function Page() {
  const filesResource = useFiles();
  const alertsResource = useAlerts(filesResource.data ? hasPending(filesResource.data) : false);

  const [showModal, setShowModal] = useState(false);

  const upload = useUploadFile(() => {
    setShowModal(false);
    void filesResource.refresh();
    void alertsResource.refresh();
  });

  function handleRefresh() {
    void filesResource.refresh();
    void alertsResource.refresh();
  }

  const errorMessage = filesResource.error ?? alertsResource.error ?? upload.error;

  return (
    <Container fluid className="py-4 px-4 bg-light min-vh-100">
      <Row className="justify-content-center">
        <Col xxl={10} xl={11}>
          <Card className="shadow-sm border-0 mb-4">
            <Card.Body className="p-4">
              <div className="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                <div>
                  <h1 className="h3 mb-2">Управление файлами</h1>
                  <p className="text-secondary mb-0">
                    Загрузка файлов, просмотр статусов обработки и ленты алертов.
                  </p>
                </div>
                <div className="d-flex gap-2">
                  <Button variant="outline-secondary" onClick={handleRefresh}>
                    Обновить
                  </Button>
                  <Button variant="primary" onClick={() => setShowModal(true)}>
                    Добавить файл
                  </Button>
                </div>
              </div>
            </Card.Body>
          </Card>

          {errorMessage ? (
            <Alert variant="danger" className="shadow-sm">
              {errorMessage}
            </Alert>
          ) : null}

          <FilesTable
            files={filesResource.data ?? []}
            isLoading={filesResource.isLoading}
            downloadUrl={downloadUrl}
          />

          <AlertsTable alerts={alertsResource.data ?? []} isLoading={alertsResource.isLoading} />
        </Col>
      </Row>

      <UploadFileModal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={upload.title}
        onTitleChange={upload.setTitle}
        onFileChange={upload.setSelectedFile}
        isSubmitting={upload.isSubmitting}
        onSubmit={upload.submit}
      />
    </Container>
  );
}
