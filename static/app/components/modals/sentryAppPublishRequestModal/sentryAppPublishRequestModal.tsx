import {Fragment, useState} from 'react';
import styled from '@emotion/styled';

import {addErrorMessage, addSuccessMessage} from 'sentry/actionCreators/indicator';
import type {ModalRenderProps} from 'sentry/actionCreators/modal';
import Form from 'sentry/components/forms/form';
import JsonForm from 'sentry/components/forms/jsonForm';
import FormModel from 'sentry/components/forms/model';
import {INTEGRATION_CATEGORIES} from 'sentry/components/modals/sentryAppPublishRequestModal/sentryAppUtils';
import {t, tct} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import type {SentryApp} from 'sentry/types/integrations';
import type {Organization} from 'sentry/types/organization';
import {safeURL} from 'sentry/utils/url/safeURL';

function transformData(data: Record<string, any>, model: FormModel) {
  // map object to list of questions
  const questionnaire = Array.from(model.fieldDescriptor.values()).map(field =>
    // we read the meta for the question that has a react node for the label
    ({
      question: field.meta || field.label,
      answer: data[field.name],
    })
  );
  return {questionnaire};
}

type Props = ModalRenderProps & {
  app: SentryApp;
  onPublishSubmission: () => void;
  organization: Organization;
};

export function SentryAppPublishRequestModal(props: Props) {
  const [formModel] = useState<FormModel>(() => new FormModel({transformData}));
  const {app, closeModal, Header, Body, onPublishSubmission} = props;

  const formFields = () => {
    // No translations since we need to be able to read this email :)
    const baseFields: React.ComponentProps<typeof JsonForm>['fields'] = [
      {
        type: 'textarea',
        required: true,
        label: t(
          'Provide a description about your integration, how this benefits developers using Sentry along with what’s needed to set up this integration.'
        ),
        meta: 'Provide a description about your integration, how this benefits developers using Sentry along with what’s needed to set up this integration.',
        autosize: true,
        rows: 1,
        inline: false,
        name: 'question0',
      },
      {
        type: 'textarea',
        required: true,
        meta: 'Provide a one-liner describing your integration. Subject to approval, we’ll use this to describe your integration on Sentry Integrations.',
        label: (
          <Fragment>
            {t(
              'Provide a one-liner describing your integration. Subject to approval, we’ll use this to describe your integration on '
            )}
            <a target="_blank" href="https://sentry.io/integrations/" rel="noreferrer">
              {t('Sentry Integrations')}
            </a>
            .
          </Fragment>
        ),
        autosize: true,
        rows: 1,
        inline: false,
        name: 'question1',
      },
      {
        type: 'select',
        required: true,
        meta: 'Select what category best describes your integration.',
        label: (
          <Fragment>
            {t('Select what category best describes your integration. ')}
            <a
              target="_blank"
              href="https://docs.sentry.io/organization/integrations/"
              rel="noreferrer"
            >
              {t('Documentation for reference.')}
            </a>
          </Fragment>
        ),
        autosize: true,
        choices: INTEGRATION_CATEGORIES,
        rows: 1,
        inline: false,
        name: 'question2',
      },
      {
        type: 'url',
        required: true,
        label: t('Link to your documentation page.'),
        meta: 'Link to your documentation page.',
        autosize: true,
        rows: 1,
        inline: false,
        name: 'question3',
        validate: ({id, form}) =>
          safeURL(form[id])
            ? []
            : [[id, t('Invalid link: URL must start with https://')]],
      },
      {
        type: 'email',
        required: true,
        label: t('Email address for user support.'),
        meta: 'Email address for user support.',
        autosize: true,
        rows: 1,
        inline: false,
        name: 'supportEmail',
      },
      {
        type: 'url',
        required: true,
        label: t(
          'Link to a video showing installation, setup and user flow for your submission.'
        ),
        meta: 'Link to a video showing installation, setup and user flow for your submission.',
        autosize: true,
        rows: 1,
        inline: false,
        name: 'question4',
        validate: ({id, form}) =>
          safeURL(form[id])
            ? []
            : [[id, t('Invalid link: URL must start with https://')]],
      },
    ];

    return baseFields;
  };

  const handleSubmitSuccess = () => {
    addSuccessMessage(t('Request to publish %s successful.', app.slug));
    closeModal();
    onPublishSubmission();
  };

  const handleSubmitError = (err: any) => {
    addErrorMessage(
      tct('Request to publish [app] fails. [detail]', {
        app: app.slug,
        detail: err?.responseJSON?.detail,
      })
    );
  };

  const endpoint = `/sentry-apps/${app.slug}/publish-request/`;
  const forms = [
    {
      title: t('Questions to answer'),
      fields: formFields(),
    },
  ];

  const renderFooter = () => {
    return (
      <Footer>
        <FooterParagraph>
          {t(
            'By submitting your integration, you acknowledge and agree that Sentry reserves the right to remove your integration at any time in its sole discretion.'
          )}
        </FooterParagraph>
        <FooterParagraph>
          {t(
            'After submission, our team will review your integration to ensure it meets our guidelines. Our current processing time for integration publishing requests is 4 weeks. You’ll hear from us once the integration is approved or if any changes are required.'
          )}
        </FooterParagraph>
        <FooterParagraph>
          {t(
            'You must notify Sentry of any changes or modifications to the integration after publishing. We encourage you to maintain a changelog of modifications on your docs page.'
          )}
        </FooterParagraph>
        <p>{t('Thank you for contributing to the Sentry community!')}</p>
      </Footer>
    );
  };
  return (
    <Fragment>
      <Header>
        <h1>{t('Publish Request Questionnaire')}</h1>
      </Header>
      <Body>
        <Explanation>
          {t(
            `Please fill out this questionnaire in order to get your integration evaluated for publication.
              Once your integration has been approved, users outside of your organization will be able to install it.`
          )}
        </Explanation>
        <Form
          allowUndo
          apiMethod="POST"
          apiEndpoint={endpoint}
          onSubmitSuccess={handleSubmitSuccess}
          onSubmitError={handleSubmitError}
          model={formModel}
          submitLabel={t('Request Publication')}
          onCancel={closeModal}
        >
          <JsonForm forms={forms} />
          {renderFooter()}
        </Form>
      </Body>
    </Fragment>
  );
}

const Explanation = styled('div')`
  margin: ${space(1.5)} 0px;
  font-size: ${p => p.theme.fontSize.md};
`;

const Footer = styled('div')`
  font-size: ${p => p.theme.fontSize.md};
`;

const FooterParagraph = styled(`p`)`
  margin-bottom: ${space(1)};
`;
