export default function Fonte({ source }) {
  if (!source) return null;
  return (
    <footer className="fonte">
      Fonte: <code>{source.view}</code> ({source.layer})
    </footer>
  );
}
