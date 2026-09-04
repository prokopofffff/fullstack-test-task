import type { Metadata } from "next";
import 'bootstrap/dist/css/bootstrap.min.css';
import { Container } from "react-bootstrap";

export const metadata: Metadata = {
  title: "Тестовое задание Fullstack",
  description: "Тестовое задание Fullstack",
};

export default async function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang='ru'>
      <body>
        <Container fluid className='p-0'>
            {children}
        </Container>
      </body>
    </html>
  );
}
