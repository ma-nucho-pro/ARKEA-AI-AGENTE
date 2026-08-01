'use strict';

function shouldAttachArkeaToken(details, trustedOrigin) {
  let targetIsTrusted = false;
  try {
    targetIsTrusted = new URL(details.url).origin === trustedOrigin;
  } catch {
    targetIsTrusted = false;
  }
  const initialMainFrame = details.resourceType === 'mainFrame'
    && details.url === `${trustedOrigin}/`;
  const trustedRenderer = details.initiator === trustedOrigin;
  const trustedTopFrame = targetIsTrusted
    && details.frameId === 0
    && details.resourceType !== 'subFrame';
  let trustedElectronFrame = false;
  try {
    trustedElectronFrame = targetIsTrusted
      && details.frame?.parent == null
      && new URL(details.frame?.url).origin === trustedOrigin;
  } catch {
    trustedElectronFrame = false;
  }

  let sandboxedPreviewFrame = false;
  try {
    sandboxedPreviewFrame = details.frame?.url === 'about:srcdoc'
      && new URL(details.frame?.parent?.url).origin === trustedOrigin;
  } catch {
    sandboxedPreviewFrame = false;
  }

  let opaquePreviewMedia = false;
  if (
    (details.initiator === 'null' || sandboxedPreviewFrame)
    && (details.resourceType === 'image' || details.resourceType === 'media')
  ) {
    try {
      const target = new URL(details.url);
      opaquePreviewMedia = target.origin === trustedOrigin
        && (
          target.pathname.startsWith('/data/generated/')
          || target.pathname.startsWith('/data/uploads/')
        );
    } catch {
      opaquePreviewMedia = false;
    }
  }

  return initialMainFrame
    || trustedRenderer
    || trustedTopFrame
    || trustedElectronFrame
    || opaquePreviewMedia;
}

module.exports = {shouldAttachArkeaToken};
