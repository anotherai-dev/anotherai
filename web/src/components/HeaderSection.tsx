type Props = {
  title: string;
  description: string;
  className?: string;
};

export function HeaderSection(props: Props) {
  const { title, description, className } = props;

  return (
    <div className={className}>
      <h1 className="text-2xl font-semibold text-gray-900 mb-2">{title}</h1>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}
